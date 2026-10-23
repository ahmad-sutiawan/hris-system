"""Waktu server dan shift terdaftar untuk absen mobile."""

from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone

from apps.attendance.services.punch_work_date import resolve_punch_work_date
from apps.shifts.models import ShiftAssignment


def _aware(day, clock_time):
    if clock_time is None:
        return None
    combined = datetime.combine(day, clock_time)
    if timezone.is_naive(combined):
        combined = timezone.make_aware(combined, timezone.get_current_timezone())
    return combined.isoformat()


def matched_shift_payload(employee, when, *, is_clock_out: bool) -> dict | None:
    """Shift yang sudah dijadwalkan untuk waktu server ini. Tidak membuat jadwal baru."""
    if employee is None:
        return None
    work_date = resolve_punch_work_date(employee, when, is_clock_out=is_clock_out)
    assignment = (
        ShiftAssignment.objects.filter(employee=employee, work_date=work_date)
        .select_related("shift")
        .first()
    )
    if assignment is None or assignment.shift_id is None:
        return None
    shift = assignment.shift
    check_in = assignment.scheduled_check_in
    check_out = assignment.scheduled_check_out
    checkout_day = work_date
    if check_in and check_out and check_out <= check_in:
        checkout_day = work_date + timedelta(days=1)
    return {
        "work_date": work_date.isoformat(),
        "shift_code": shift.code,
        "shift_name": shift.name,
        "scheduled_check_in": _aware(work_date, check_in),
        "scheduled_check_out": _aware(checkout_day, check_out),
    }


def server_punch_context(employee, *, is_clock_out: bool) -> dict:
    now = timezone.now()
    return {
        "server_time": timezone.localtime(now).isoformat(),
        "matched_shift": matched_shift_payload(employee, now, is_clock_out=is_clock_out),
    }
