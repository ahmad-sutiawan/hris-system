import hashlib
from decimal import Decimal

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.attendance.models import DailyTimesheet
from apps.employees.models import Employee
from apps.payroll.models import PayrollRun, Payslip
from apps.payroll.services.calculator import (
    calc_alpha_deduction,
    calc_bpjs_jht,
    calc_bpjs_jp,
    calc_bpjs_kes,
    calc_ot_pay,
    calc_pph21,
    monthly_base,
)
from apps.payroll.services.payslip_pdf import generate_payslip_pdf


class PayrollError(Exception):
    pass


def _aggregate_timesheets(employee, period_start, period_end):
    qs = DailyTimesheet.objects.filter(
        employee=employee,
        work_date__gte=period_start,
        work_date__lte=period_end,
    )
    ot_after = sum(ts.ot_after_minutes for ts in qs)
    alpha_days = qs.filter(attendance_code__code="A").count()
    paid_hours = sum(ts.paid_working_hours for ts in qs)
    return {
        "ot_after_minutes": ot_after,
        "alpha_days": alpha_days,
        "paid_hours": paid_hours,
    }


@transaction.atomic
def calculate_payroll_run(payroll_run: PayrollRun) -> PayrollRun:
    if payroll_run.status == PayrollRun.Status.FINALIZED:
        raise PayrollError("Payroll sudah finalized.")

    employees = Employee.objects.filter(
        tenant=payroll_run.tenant,
        plant=payroll_run.plant,
    ).exclude(status__in=[Employee.Status.INACTIVE, Employee.Status.RESIGNED])

    Payslip.objects.filter(payroll_run=payroll_run).delete()

    for employee in employees:
        stats = _aggregate_timesheets(
            employee,
            payroll_run.period_start,
            payroll_run.period_end,
        )
        base = monthly_base(employee)
        ot_pay = calc_ot_pay(employee, stats["ot_after_minutes"])
        alpha_deduction = calc_alpha_deduction(employee, stats["alpha_days"])
        gross = base + ot_pay

        bpjs_kes = calc_bpjs_kes(employee)
        bpjs_jht = calc_bpjs_jht(employee)
        bpjs_jp = calc_bpjs_jp(employee)
        pph21 = calc_pph21(gross, employee.tax_status)

        deductions = bpjs_kes + bpjs_jht + bpjs_jp + pph21 + alpha_deduction
        net = gross - deductions

        earnings = {
            "base_salary": str(base),
            "ot_after": str(ot_pay),
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
        "employee", "payroll_run", "payroll_run__plant"
    ):
        pdf_bytes = generate_payslip_pdf(payslip)
        filename = f"slip_{payslip.employee.employee_id}_{payroll_run.period_end}.pdf"
        payslip.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)

    DailyTimesheet.objects.filter(
        tenant=payroll_run.tenant,
        plant=payroll_run.plant,
        work_date__gte=payroll_run.period_start,
        work_date__lte=payroll_run.period_end,
    ).update(calculation_status=DailyTimesheet.CalculationStatus.LOCKED)

    return payroll_run
