from datetime import datetime, timedelta
from decimal import Decimal

from django.utils import timezone


def _combine(work_date, time_value, tz):
    naive = datetime.combine(work_date, time_value)
    return timezone.make_aware(naive, tz) if timezone.is_naive(naive) else naive


def _minutes_between(start_dt, end_dt):
    if not start_dt or not end_dt or end_dt <= start_dt:
        return 0
    return int((end_dt - start_dt).total_seconds() // 60)


def _decimal_hours(minutes, break_minutes=0):
    effective = max(0, minutes - break_minutes)
    return (Decimal(effective) / Decimal("60")).quantize(Decimal("0.01"))


def calculate_timesheet_metrics(
    *,
    work_date,
    scheduled_check_in,
    scheduled_check_out,
    check_in,
    check_out,
    break_minutes=0,
    grace_period_minutes=15,
    schedule_working_hours=None,
    hourly_time_off_taken=Decimal("0"),
    ot_before_enabled=False,
):
    tz = timezone.get_current_timezone()
    sched_in = (
        _combine(work_date, scheduled_check_in, tz)
        if scheduled_check_in
        else None
    )
    sched_out = (
        _combine(work_date, scheduled_check_out, tz)
        if scheduled_check_out
        else None
    )
    if sched_out and sched_in and sched_out <= sched_in:
        sched_out += timedelta(days=1)

    late_in = 0
    if check_in and sched_in:
        diff = _minutes_between(sched_in, check_in)
        late_in = max(0, diff - grace_period_minutes)

    early_out = 0
    if check_out and sched_out:
        diff = _minutes_between(check_out, sched_out)
        early_out = max(0, diff - grace_period_minutes)

    ot_before = 0
    if ot_before_enabled and check_in and sched_in and check_in < sched_in:
        ot_before = _minutes_between(check_in, sched_in)

    ot_after = 0
    if check_out and sched_out and check_out > sched_out:
        ot_after = _minutes_between(sched_out, check_out)

    schedule_hours = schedule_working_hours or Decimal("0")
    if schedule_hours == 0 and sched_in and sched_out:
        schedule_hours = _decimal_hours(_minutes_between(sched_in, sched_out), break_minutes)

    actual_hours = Decimal("0")
    if check_in and check_out:
        worked_minutes = _minutes_between(check_in, check_out)
        actual_hours = _decimal_hours(worked_minutes, break_minutes)
        actual_hours = max(Decimal("0"), actual_hours - hourly_time_off_taken)

    paid_hours = actual_hours
    if schedule_hours > 0:
        paid_hours = min(actual_hours, schedule_hours)
    late_deduction = _decimal_hours(late_in)
    early_deduction = _decimal_hours(early_out)
    paid_hours = max(Decimal("0"), paid_hours - late_deduction - early_deduction)
    ot_hours = _decimal_hours(ot_after)
    paid_hours += ot_hours

    return {
        "late_in_minutes": late_in,
        "early_out_minutes": early_out,
        "schedule_working_hours": schedule_hours,
        "actual_working_hours": actual_hours,
        "paid_working_hours": paid_hours.quantize(Decimal("0.01")),
        "ot_before_minutes": ot_before,
        "ot_after_minutes": ot_after,
    }
