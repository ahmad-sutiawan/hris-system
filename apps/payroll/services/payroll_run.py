import hashlib
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.attendance.models import DailyTimesheet
from apps.core.models import Notification
from apps.core.services.notifications import notify_user
from apps.employees.models import Employee
from apps.payroll.models import PayrollRun, Payslip
from apps.payroll.services.ter import build_ter_cache
from apps.web.formatting import format_rupiah
from apps.payroll.services.aggregation import bulk_overtime_pay, bulk_timesheet_stats
from apps.payroll.services.shift_allowance import bulk_shift_allowance_pay
from apps.payroll.services.calculator import (
    calc_alpha_deduction,
    calc_bpjs_jht,
    calc_bpjs_jp,
    calc_bpjs_kes,
    calc_daily_allowances,
    calc_period_base,
    calc_pph21,
)
from apps.payroll.services.payslip_pdf import generate_payslip_pdf


class PayrollError(Exception):
    pass


@transaction.atomic
def calculate_payroll_run(payroll_run: PayrollRun) -> PayrollRun:
    if payroll_run.status == PayrollRun.Status.FINALIZED:
        raise PayrollError("Payroll sudah finalized.")

    employees = list(
        Employee.objects.filter(
            tenant=payroll_run.tenant,
            plant=payroll_run.plant,
        )
        .exclude(status__in=[Employee.Status.INACTIVE, Employee.Status.RESIGNED])
        .select_related("tenant")
    )

    Payslip.objects.filter(payroll_run=payroll_run).delete()

    employee_ids = [e.pk for e in employees]
    timesheet_stats = bulk_timesheet_stats(
        employee_ids,
        payroll_run.period_start,
        payroll_run.period_end,
    )
    overtime_stats = bulk_overtime_pay(
        employees,
        payroll_run.period_start,
        payroll_run.period_end,
    )
    shift_allowance_stats = bulk_shift_allowance_pay(
        employee_ids,
        payroll_run.period_start,
        payroll_run.period_end,
        tenant=payroll_run.tenant,
    )
    ter_cache = build_ter_cache(payroll_run.tenant)

    for employee in employees:
        stats = timesheet_stats[employee.pk]
        ot_total, ot_detail = overtime_stats[employee.pk]
        shift_allowance_total, shift_allowance_breakdown = shift_allowance_stats[employee.pk]
        ot_before_pay = ot_detail["ot_before"]
        ot_after_pay = ot_detail["ot_after"]

        present_days = stats["present_days"]
        base = calc_period_base(employee, present_days=present_days)
        allowance_total, allowance_breakdown = calc_daily_allowances(
            employee, present_days=present_days
        )
        alpha_deduction = calc_alpha_deduction(employee, stats["alpha_days"])
        gross = base + allowance_total + ot_total + shift_allowance_total

        bpjs_kes = calc_bpjs_kes(employee)
        bpjs_jht = calc_bpjs_jht(employee)
        bpjs_jp = calc_bpjs_jp(employee)
        pph21 = calc_pph21(gross, employee, ter_cache=ter_cache)

        deductions = bpjs_kes + bpjs_jht + bpjs_jp + pph21 + alpha_deduction
        net = gross - deductions

        earnings = {
            "base_salary": str(base),
            "ot_total": str(ot_total),
            "ot_after": str(ot_after_pay),
        }
        for key, amount in allowance_breakdown.items():
            earnings[key] = str(amount)
        for key, amount in shift_allowance_breakdown.items():
            earnings[key] = amount
        if allowance_total > 0:
            earnings["allowance_daily_total"] = str(allowance_total)
        if shift_allowance_total > 0:
            earnings["shift_allowance_total"] = str(shift_allowance_total)
        if ot_before_pay > 0:
            earnings["ot_before"] = str(ot_before_pay)
        if ot_detail["by_type"]:
            earnings["ot_by_type"] = {
                code: str(amount) for code, amount in ot_detail["by_type"].items()
            }
        deductions_breakdown = {
            "bpjs_kesehatan": str(bpjs_kes),
            "bpjs_jht": str(bpjs_jht),
            "bpjs_jp": str(bpjs_jp),
            "pph21": str(pph21),
            "alpha": str(alpha_deduction),
        }

        verification = hashlib.sha256(
            f"{employee.id}:{payroll_run.id}:{net}".encode()
        ).hexdigest()[:16]

        Payslip.objects.create(
            tenant=payroll_run.tenant,
            payroll_run=payroll_run,
            employee=employee,
            gross_amount=gross,
            deduction_amount=deductions,
            net_amount=net,
            earnings_breakdown=earnings,
            deductions_breakdown=deductions_breakdown,
            verification_hash=verification,
        )

    payroll_run.status = PayrollRun.Status.REVIEW
    payroll_run.save(update_fields=["status", "updated_at"])
    return payroll_run


@transaction.atomic
def finalize_payroll_run(payroll_run: PayrollRun) -> PayrollRun:
    if payroll_run.status not in {PayrollRun.Status.REVIEW, PayrollRun.Status.DRAFT}:
        raise PayrollError("Payroll tidak bisa difinalize.")

    negative = Payslip.objects.filter(payroll_run=payroll_run, net_amount__lt=0)
    if negative.exists():
        raise PayrollError("Ada slip gaji dengan THP negatif.")

    payroll_run.status = PayrollRun.Status.FINALIZED
    payroll_run.finalized_at = timezone.now()
    payroll_run.save(update_fields=["status", "finalized_at", "updated_at"])

    for payslip in Payslip.objects.filter(payroll_run=payroll_run).select_related(
        "employee", "employee__user", "payroll_run", "payroll_run__plant"
    ):
        pdf_bytes = generate_payslip_pdf(payslip)
        filename = f"slip_{payslip.employee.employee_id}_{payroll_run.period_end}.pdf"
        payslip.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
        if payslip.employee.user_id:
            notify_user(
                tenant=payroll_run.tenant,
                user=payslip.employee.user,
                category=Notification.Category.PAYROLL,
                title="Slip gaji tersedia",
                message=(
                    f"Slip gaji periode {payroll_run.period_start} — {payroll_run.period_end} "
                    f"siap diunduh. THP: {format_rupiah(payslip.net_amount)}"
                ),
                link=f"{settings.HRIS_SITE_URL}/payslips/{payslip.pk}/download/",
            )

    DailyTimesheet.objects.filter(
        tenant=payroll_run.tenant,
        plant=payroll_run.plant,
        work_date__gte=payroll_run.period_start,
        work_date__lte=payroll_run.period_end,
    ).update(
        calculation_status=DailyTimesheet.CalculationStatus.LOCKED,
        locked_at=timezone.now(),
    )

    return payroll_run
