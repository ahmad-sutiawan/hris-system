from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.employees.models import Employee
from apps.payroll.models import THRPayslip, THRRun
from apps.payroll.services.calculator import monthly_base


class THRError(Exception):
    pass


def _months_worked_in_year(employee, year: int) -> int:
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    join = employee.join_date or start
    resign = employee.resign_date
    period_start = max(join, start)
    period_end = min(resign or end, end)
    if period_end < period_start:
        return 0
    months = (period_end.year - period_start.year) * 12 + (period_end.month - period_start.month) + 1
    return max(0, min(12, months))


@transaction.atomic
def calculate_thr_run(thr_run: THRRun) -> THRRun:
    if thr_run.status == THRRun.Status.FINALIZED:
        raise THRError("THR sudah finalized.")

    employees = Employee.objects.filter(
        tenant=thr_run.tenant,
        plant=thr_run.plant,
    ).exclude(status__in=[Employee.Status.INACTIVE, Employee.Status.RESIGNED])

    THRPayslip.objects.filter(thr_run=thr_run).delete()

    for employee in employees:
        months = _months_worked_in_year(employee, thr_run.year)
        if months <= 0:
            continue
        base_ref = monthly_base(employee)
        thr_amount = (base_ref * Decimal(months) / Decimal("12")).quantize(Decimal("0.01"))
        THRPayslip.objects.create(
            tenant=thr_run.tenant,
            thr_run=thr_run,
            employee=employee,
            months_worked=months,
            base_reference=base_ref,
            thr_amount=thr_amount,
        )

    return thr_run


@transaction.atomic
def finalize_thr_run(thr_run: THRRun) -> THRRun:
    if not THRPayslip.objects.filter(thr_run=thr_run).exists():
        raise THRError("Hitung THR terlebih dahulu.")
    thr_run.status = THRRun.Status.FINALIZED
    thr_run.finalized_at = timezone.now()
    thr_run.save(update_fields=["status", "finalized_at", "updated_at"])
    return thr_run
