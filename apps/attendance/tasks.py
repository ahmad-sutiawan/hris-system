"""Background jobs for attendance (RQ worker)."""

from __future__ import annotations

from datetime import date

from django.utils.dateparse import parse_date


def recalculate_timesheet_job(employee_id: int, work_date_str: str) -> str:
    """Recalculate one daily timesheet — safe to run concurrently per employee/date."""
    from apps.attendance.services.timesheet import recalculate_daily_timesheet
    from apps.employees.models import Employee

    work_date = parse_date(work_date_str)
    if work_date is None:
        raise ValueError(f"Invalid work_date: {work_date_str!r}")

    employee = Employee.objects.select_related("tenant", "plant").get(pk=employee_id)
    recalculate_daily_timesheet(employee, work_date)
    return f"{employee_id}:{work_date.isoformat()}"
