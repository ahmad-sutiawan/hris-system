from decimal import Decimal

from django.utils import timezone

from apps.core.xlsx_io import write_xlsx

TIMESHEET_EXPORT_HEADERS = [
    "Employee ID",
    "Full Name",
    "Branch",
    "Branch Code",
    "Organization",
    "Job Position",
    "Date",
    "Shift",
    "Shift Code",
    "Shift Label",
    "Schedule Check In",
    "Schedule Check Out",
    "Attendance Code",
    "Time Off Code",
    "Hourly Time Off Start & Finish",
    "Check In",
    "Check Out",
    "Late In",
    "Early Out",
    "Effective Working Hour",
    "Actual Working Hour",
    "Brief Working Hour",
    "Overtime Before",
    "Overtime Duration After Hourly Time Off Label",
    "Hourly Time Off Taken",
    "Calculation Status",
    "Calculated At",
    "Locked At",
]


def _fmt_time(value):
    return value.strftime("%H:%M") if value else ""


def _fmt_punch_time(value):
    if not value:
        return ""
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime("%H:%M")


def _fmt_punch_datetime(value):
    if not value:
        return ""
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")


def _fmt_duration_minutes(minutes) -> str:
    total = int(minutes or 0)
    hours, mins = divmod(total, 60)
    return f"{hours:02d}:{mins:02d}"


def _fmt_duration_hours(hours) -> str:
    if hours is None:
        return "00:00"
    total_minutes = int(Decimal(str(hours)) * 60)
    hours_part, mins = divmod(total_minutes, 60)
    return f"{hours_part:02d}:{mins:02d}"


def _fmt_hourly_time_off_breakdown(breakdown) -> str:
    if not breakdown:
        return ""
    parts = []
    for item in breakdown:
        if isinstance(item, dict):
            start = (
                item.get("start")
                or item.get("start_time")
                or item.get("from")
                or ""
            )
            finish = (
                item.get("finish")
                or item.get("end")
                or item.get("end_time")
                or item.get("to")
                or ""
            )
            if start or finish:
                parts.append(f"{start} - {finish}".strip(" -"))
        elif isinstance(item, str):
            parts.append(item)
    return "; ".join(parts)


def timesheet_to_row(ts):
    emp = ts.employee
    branch = ts.plant.name if ts.plant_id else ""
    branch_code = ts.plant.code if ts.plant_id else ""
    return [
        emp.employee_id,
        emp.full_name,
        branch,
        branch_code,
        emp.department.name if emp.department_id else "",
        emp.job_position.title if emp.job_position_id else "",
        ts.work_date.isoformat(),
        ts.shift.name if ts.shift_id else "",
        ts.shift_code,
        ts.shift_label,
        _fmt_time(ts.scheduled_check_in),
        _fmt_time(ts.scheduled_check_out),
        ts.attendance_code.code if ts.attendance_code_id else "",
        ts.time_off_code,
        _fmt_hourly_time_off_breakdown(ts.hourly_time_off_breakdown),
        _fmt_punch_time(ts.check_in),
        _fmt_punch_time(ts.check_out),
        _fmt_duration_minutes(ts.late_in_minutes),
        _fmt_duration_minutes(ts.early_out_minutes),
        _fmt_duration_hours(ts.schedule_working_hours),
        _fmt_duration_hours(ts.actual_working_hours),
        _fmt_duration_hours(ts.paid_working_hours),
        _fmt_duration_minutes(ts.ot_before_minutes),
        _fmt_duration_minutes(ts.ot_after_minutes),
        _fmt_duration_hours(ts.hourly_time_off_taken),
        ts.get_calculation_status_display(),
        _fmt_punch_datetime(ts.calculated_at),
        _fmt_punch_datetime(ts.locked_at),
    ]


def export_timesheets_xlsx(timesheets) -> bytes:
    return write_xlsx(TIMESHEET_EXPORT_HEADERS, (timesheet_to_row(ts) for ts in timesheets))


# Backward-compatible alias.
export_timesheets_csv = export_timesheets_xlsx
