"""Resolve work_date for punch — supports cross-day night shifts."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.shifts.models import ShiftAssignment


def _in_cross_day_morning_tail(assignment, local_time: time) -> bool:
    """True when local clock time is still within the morning leg of a cross-day shift."""
    if not assignment or not assignment.shift.cross_day:
        return False
    sched_out = assignment.scheduled_check_out
    # Cross-day: checkout is on the next calendar day (e.g. 06:00 after 22:00 start).
    return local_time <= sched_out


def resolve_punch_work_date(employee, when: datetime, *, is_clock_out: bool = False) -> date:
    local_dt = timezone.localtime(when)
    local_date = local_dt.date()
    local_time = local_dt.time()

    if is_clock_out:
        open_record = (
            AttendanceRecord.objects.filter(
                employee=employee,
                check_in__isnull=False,
                check_out__isnull=True,
            )
            .order_by("-work_date")
            .first()
        )
        if open_record:
            assignment = ShiftAssignment.objects.filter(
                employee=employee,
                work_date=open_record.work_date,
            ).select_related("shift").first()
            if assignment and assignment.shift.cross_day:
                return open_record.work_date
            if open_record.work_date == local_date:
                return open_record.work_date

        yesterday = local_date - timedelta(days=1)
        y_assignment = ShiftAssignment.objects.filter(
            employee=employee,
            work_date=yesterday,
        ).select_related("shift").first()
        if y_assignment and y_assignment.shift.cross_day:
            if _in_cross_day_morning_tail(y_assignment, local_time):
                return yesterday

        if open_record:
            return open_record.work_date

    if not is_clock_out:
        yesterday = local_date - timedelta(days=1)
        y_assignment = ShiftAssignment.objects.filter(
            employee=employee,
            work_date=yesterday,
        ).select_related("shift").first()
        if y_assignment and _in_cross_day_morning_tail(y_assignment, local_time):
            y_record = AttendanceRecord.objects.filter(
                employee=employee,
                work_date=yesterday,
            ).first()
            if not y_record or not y_record.check_in or not y_record.check_out:
                return yesterday

    assignment = ShiftAssignment.objects.filter(
        employee=employee,
        work_date=local_date,
    ).select_related("shift").first()
    if assignment:
        return local_date

    return local_date
