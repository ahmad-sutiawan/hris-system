import csv
from io import StringIO

TIMESHEET_EXPORT_HEADERS = [
    "Employee ID",
    "Full Name",
    "Branch",
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
    "Hourly Time Off Breakdown",
    "Check In",
    "Check Out",
    "Late In",
    "Early Out",
    "Schedule Working Hour",
    "Actual Working Hour",
    "Paid Working Hour",
    "Overtime Duration Before",
    "Overtime Duration After",
    "Hourly Time Off Taken",
]


def _fmt_time(value):
    return value.strftime("%H:%M") if value else ""


def _fmt_dt(value):
    return value.strftime("%Y-%m-%d %H:%M") if value else ""


def timesheet_to_row(ts):
    emp = ts.employee
    branch = ""
    if ts.plant_id:
        branch = ts.plant.get_branch_type_display() or ts.plant.code
    return [
        emp.employee_id,
        emp.full_name,
        branch,
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
        str(ts.hourly_time_off_breakdown or ""),
        _fmt_dt(ts.check_in),
        _fmt_dt(ts.check_out),
        ts.late_in_minutes,
        ts.early_out_minutes,
        ts.schedule_working_hours,
        ts.actual_working_hours,
        ts.paid_working_hours,
        ts.ot_before_minutes,
        ts.ot_after_minutes,
        ts.hourly_time_off_taken,
    ]


def export_timesheets_csv(timesheets):
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(TIMESHEET_EXPORT_HEADERS)
    for ts in timesheets:
        writer.writerow(timesheet_to_row(ts))
    return buffer.getvalue()
