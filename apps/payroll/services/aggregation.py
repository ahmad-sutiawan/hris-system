from decimal import Decimal

from apps.attendance.models import DailyTimesheet, OvertimeRequest
from apps.payroll.services.calculator import OT_HOURLY_MULTIPLIER, calc_ot_pay


def bulk_timesheet_stats(employee_ids, period_start, period_end) -> dict[int, dict]:
    """Agregasi timesheet per karyawan dalam satu query (hindari N+1 di payroll run)."""
    defaults = {
        "ot_after_minutes": 0,
        "ot_before_minutes": 0,
        "alpha_days": 0,
        "paid_hours": Decimal("0"),
        "present_days": 0,
    }
    stats = {eid: dict(defaults) for eid in employee_ids}

    if not employee_ids:
        return stats

    rows = (
        DailyTimesheet.objects.filter(
            employee_id__in=employee_ids,
            work_date__gte=period_start,
            work_date__lte=period_end,
        )
        .select_related("attendance_code")
        .only(
            "employee_id",
            "ot_after_minutes",
            "ot_before_minutes",
            "paid_working_hours",
            "check_in",
            "attendance_code__code",
        )
    )

    for ts in rows:
        bucket = stats[ts.employee_id]
        bucket["ot_after_minutes"] += ts.ot_after_minutes
        bucket["ot_before_minutes"] += ts.ot_before_minutes
        bucket["paid_hours"] += ts.paid_working_hours
        code = ts.attendance_code.code if ts.attendance_code_id else ""
        if code == "A":
            bucket["alpha_days"] += 1
        elif ts.check_in is not None:
            bucket["present_days"] += 1

    return stats


def bulk_overtime_pay(employees, period_start, period_end) -> dict[int, tuple[Decimal, dict]]:
    """
    Hitung lembur semua karyawan: 2 query (OT requests + timesheets), bukan per karyawan.
    """
    employee_ids = [e.pk for e in employees]
    employees_by_id = {e.pk: e for e in employees}
    empty_detail = {"by_type": {}, "ot_before": Decimal("0"), "ot_after": Decimal("0")}
    result = {eid: (Decimal("0"), dict(empty_detail)) for eid in employee_ids}

    if not employee_ids:
        return result

    approved = OvertimeRequest.objects.filter(
        employee_id__in=employee_ids,
        work_date__gte=period_start,
        work_date__lte=period_end,
        status=OvertimeRequest.Status.APPROVED,
    ).select_related("overtime_type")

    ts_index: dict[tuple[int, object], DailyTimesheet] = {}
    for ts in DailyTimesheet.objects.filter(
        employee_id__in=employee_ids,
        work_date__gte=period_start,
        work_date__lte=period_end,
    ).only("employee_id", "work_date", "ot_before_minutes", "ot_after_minutes"):
        ts_index[(ts.employee_id, ts.work_date)] = ts

    for req in approved:
        employee = employees_by_id.get(req.employee_id)
        if not employee:
            continue
        ts = ts_index.get((req.employee_id, req.work_date))
        if not ts:
            continue

        ot_before = ts.ot_before_minutes
        ot_after = ts.ot_after_minutes
        if ot_before <= 0 and ot_after <= 0:
            continue

        multiplier = (
            req.overtime_type.multiplier
            if req.overtime_type_id
            else OT_HOURLY_MULTIPLIER
        )
        code = req.overtime_type.code if req.overtime_type_id else "OT"

        before_pay = calc_ot_pay(employee, ot_before, multiplier=multiplier)
        after_pay = calc_ot_pay(employee, ot_after, multiplier=multiplier)
        pay = before_pay + after_pay

        total, detail = result[req.employee_id]
        total += pay
        detail["by_type"][code] = detail["by_type"].get(code, Decimal("0")) + pay
        detail["ot_before"] += before_pay
        detail["ot_after"] += after_pay
        result[req.employee_id] = (total, detail)

    return result
