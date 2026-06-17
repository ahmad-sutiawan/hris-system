from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.attendance.models import AttendanceCode, AttendanceRecord, DailyTimesheet, OvertimeRequest
from apps.attendance.services.policy import ot_before_overtime_enabled
from apps.attendance.services.timesheet_engine import calculate_timesheet_metrics, reconcile_paid_hours
from apps.core.models import HolidayCalendar
from apps.leave.models import LeaveRequest
from apps.shifts.models import ShiftAssignment


class TimesheetLockedError(Exception):
    pass


def _is_holiday(employee, work_date: date) -> bool:
    from django.db.models import Q

    return HolidayCalendar.objects.filter(
        tenant=employee.tenant,
        holiday_date=work_date,
        is_active=True,
    ).filter(
        Q(holiday_type=HolidayCalendar.HolidayType.NATIONAL)
        | Q(holiday_type=HolidayCalendar.HolidayType.COMPANY)
        | Q(holiday_type=HolidayCalendar.HolidayType.PLANT, plant=employee.plant)
    ).exists()


def _leave_for_date(employee, work_date):
    return LeaveRequest.objects.filter(
        employee=employee,
        status=LeaveRequest.Status.APPROVED,
        start_date__lte=work_date,
        end_date__gte=work_date,
    ).select_related("leave_type").first()


def _approved_overtime_caps(employee, work_date):
    req = OvertimeRequest.objects.filter(
        employee=employee,
        work_date=work_date,
        status=OvertimeRequest.Status.APPROVED,
    ).first()
    if not req:
        return 0, 0
    return req.ot_before_minutes, req.ot_after_minutes


def _sync_attendance_assignment(record, assignment):
    if not record or not assignment or record.shift_assignment_id == assignment.pk:
        return
    record.shift_assignment = assignment
    record.save(update_fields=["shift_assignment", "updated_at"])


@transaction.atomic
def recalculate_daily_timesheet(employee, work_date: date) -> DailyTimesheet:
    existing = DailyTimesheet.objects.filter(
        employee=employee,
        work_date=work_date,
    ).first()
    if existing and existing.calculation_status == DailyTimesheet.CalculationStatus.LOCKED:
        return existing

    assignment = ShiftAssignment.objects.filter(
        employee=employee,
        work_date=work_date,
    ).select_related("shift").first()

    record = AttendanceRecord.objects.filter(
        employee=employee,
        work_date=work_date,
    ).first()

    _sync_attendance_assignment(record, assignment)

    leave = _leave_for_date(employee, work_date)
    hadir_code = AttendanceCode.objects.filter(
        tenant=employee.tenant,
        code="H",
    ).first()

    shift = assignment.shift if assignment else None
    scheduled_in = assignment.scheduled_check_in if assignment else None
    scheduled_out = assignment.scheduled_check_out if assignment else None
    break_minutes = shift.break_minutes if shift else 0
    grace = shift.grace_period_minutes if shift else 15
    # Derive schedule cap from assignment window (supports long shift / dynamic override).
    schedule_hours = None if assignment and scheduled_in and scheduled_out else (
        shift.schedule_working_hours if shift else None
    )

    check_in = record.check_in if record else None
    check_out = record.check_out if record else None
    attendance_code = record.attendance_code if record else None
    time_off_code = ""

    if leave and not check_in:
        time_off_code = leave.leave_type.code
        cuti_code = AttendanceCode.objects.filter(
            tenant=employee.tenant,
            code="C",
        ).first()
        attendance_code = cuti_code or attendance_code
    elif not record and not leave:
        if _is_holiday(employee, work_date):
            attendance_code = None
        else:
            alpha_code = AttendanceCode.objects.filter(
                tenant=employee.tenant,
                code="A",
            ).first()
            attendance_code = alpha_code
    elif record and not attendance_code:
        attendance_code = hadir_code

    if record and _is_holiday(employee, work_date):
        time_off_code = "LIBUR"

    ot_before_enabled = ot_before_overtime_enabled(employee.tenant, employee.plant)
    metrics = calculate_timesheet_metrics(
        work_date=work_date,
        scheduled_check_in=scheduled_in,
        scheduled_check_out=scheduled_out,
        check_in=check_in,
        check_out=check_out,
        break_minutes=break_minutes,
        grace_period_minutes=grace,
        schedule_working_hours=schedule_hours,
        ot_before_enabled=ot_before_enabled,
    )

    approved_before, approved_after = _approved_overtime_caps(employee, work_date)
    metrics["ot_before_minutes"] = min(metrics["ot_before_minutes"], approved_before)
    metrics["ot_after_minutes"] = min(metrics["ot_after_minutes"], approved_after)
    reconcile_paid_hours(metrics, ot_before_enabled=ot_before_enabled)

    if attendance_code and attendance_code.code == "A":
        metrics["paid_working_hours"] = metrics["paid_working_hours"] * 0

    status = (
        existing.calculation_status
        if existing
        else DailyTimesheet.CalculationStatus.DRAFT
    )
    timesheet, _ = DailyTimesheet.objects.update_or_create(
        employee=employee,
        work_date=work_date,
        defaults={
            "tenant": employee.tenant,
            "plant": employee.plant,
            "shift": shift,
            "shift_code": shift.code if shift else "",
            "shift_label": shift.label or shift.name if shift else "",
            "scheduled_check_in": scheduled_in,
            "scheduled_check_out": scheduled_out,
            "attendance_code": attendance_code,
            "time_off_code": time_off_code,
            "check_in": check_in,
            "check_out": check_out,
            "hourly_time_off_taken": 0,
            "hourly_time_off_breakdown": [],
            "calculation_status": status,
            "calculated_at": timezone.now(),
            **metrics,
        },
    )
    return timesheet


def recalculate_timesheet_range(employee, start_date: date, end_date: date):
    current = start_date
    results = []
    while current <= end_date:
        results.append(recalculate_daily_timesheet(employee, current))
        current += timedelta(days=1)
    return results
