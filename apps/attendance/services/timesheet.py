from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from apps.attendance.models import AttendanceCode, AttendanceRecord, DailyTimesheet
from apps.attendance.services.timesheet_engine import calculate_timesheet_metrics
from apps.core.models import FeatureFlag
from apps.leave.models import LeaveRequest
from apps.shifts.models import ShiftAssignment


def _ot_before_enabled(tenant, plant):
    return FeatureFlag.objects.filter(
        tenant=tenant,
        plant=plant,
        key="ot_before_split",
        enabled=True,
    ).exists()


def _leave_for_date(employee, work_date):
    return LeaveRequest.objects.filter(
        employee=employee,
        status=LeaveRequest.Status.APPROVED,
        start_date__lte=work_date,
        end_date__gte=work_date,
    ).select_related("leave_type").first()


@transaction.atomic
def recalculate_daily_timesheet(employee, work_date: date) -> DailyTimesheet:
    assignment = ShiftAssignment.objects.filter(
        employee=employee,
        work_date=work_date,
    ).select_related("shift").first()

    record = AttendanceRecord.objects.filter(
        employee=employee,
        work_date=work_date,
    ).first()

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
    schedule_hours = shift.schedule_working_hours if shift else None

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
        alpha_code = AttendanceCode.objects.filter(
            tenant=employee.tenant,
            code="A",
        ).first()
        attendance_code = alpha_code
    elif record and not attendance_code:
        attendance_code = hadir_code

    metrics = calculate_timesheet_metrics(
        work_date=work_date,
        scheduled_check_in=scheduled_in,
        scheduled_check_out=scheduled_out,
        check_in=check_in,
        check_out=check_out,
        break_minutes=break_minutes,
        grace_period_minutes=grace,
        schedule_working_hours=schedule_hours,
        ot_before_enabled=_ot_before_enabled(employee.tenant, employee.plant),
    )

    if attendance_code and attendance_code.code == "A":
        metrics["paid_working_hours"] = metrics["paid_working_hours"] * 0

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
            "calculation_status": DailyTimesheet.CalculationStatus.DRAFT,
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
