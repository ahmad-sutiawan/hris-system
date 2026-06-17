"""HR manual attendance correction from timesheet rekap."""

from __future__ import annotations

from datetime import datetime

from django.db import transaction
from django.utils import timezone

from apps.attendance.models import AttendanceCode, AttendanceRecord, DailyTimesheet
from apps.attendance.services.timesheet import recalculate_daily_timesheet
from apps.core.models import AuditLog
from apps.core.services.audit import log_audit
from apps.shifts.models import Shift, ShiftAssignment


class CorrectionError(Exception):
    pass


def _combine(work_date, time_value):
    if not time_value:
        return None
    tz = timezone.get_current_timezone()
    naive = datetime.combine(work_date, time_value)
    return timezone.make_aware(naive, tz)


@transaction.atomic
def apply_attendance_correction(
    timesheet: DailyTimesheet,
    *,
    check_in_time=None,
    check_out_time=None,
    shift: Shift | None = None,
    scheduled_check_in=None,
    scheduled_check_out=None,
    attendance_code: AttendanceCode | None = None,
    actor=None,
) -> DailyTimesheet:
    employee = timesheet.employee
    work_date = timesheet.work_date

    if timesheet.calculation_status == DailyTimesheet.CalculationStatus.LOCKED:
        raise CorrectionError(
            "Timesheet sudah dikunci (payroll finalized). Hubungi admin untuk pembukaan."
        )

    record = AttendanceRecord.objects.filter(employee=employee, work_date=work_date).first()
    if not record:
        record = AttendanceRecord.objects.create(
            tenant=employee.tenant,
            employee=employee,
            plant=employee.plant,
            work_date=work_date,
            source=AttendanceRecord.Source.MANUAL,
        )

    if check_in_time is not None:
        record.check_in = _combine(work_date, check_in_time)
    if check_out_time is not None:
        record.check_out = _combine(work_date, check_out_time)
    if attendance_code is not None:
        record.attendance_code = attendance_code
    record.source = AttendanceRecord.Source.MANUAL
    if actor:
        record.approved_by = actor
    record.save()

    changes = {}
    if check_in_time is not None:
        changes["check_in_time"] = check_in_time.isoformat()
    if check_out_time is not None:
        changes["check_out_time"] = check_out_time.isoformat()
    if shift is not None:
        changes["shift"] = shift.code
    if scheduled_check_in is not None:
        changes["scheduled_check_in"] = scheduled_check_in.isoformat()
    if scheduled_check_out is not None:
        changes["scheduled_check_out"] = scheduled_check_out.isoformat()
    if attendance_code is not None:
        changes["attendance_code"] = attendance_code.code
    if changes:
        payload = {
            "attendance_correction": changes,
            "work_date": work_date.isoformat(),
        }
        if actor:
            payload["corrected_by"] = getattr(actor, "username", str(actor))
        log_audit(
            AuditLog.Action.UPDATE,
            record,
            changes=payload,
        )

    if shift or scheduled_check_in is not None or scheduled_check_out is not None:
        default_shift = shift or employee.default_shift
        defaults = {"shift": default_shift}
        if default_shift:
            defaults.setdefault("scheduled_check_in", default_shift.scheduled_check_in)
            defaults.setdefault("scheduled_check_out", default_shift.scheduled_check_out)
        assignment, _ = ShiftAssignment.objects.get_or_create(
            tenant=employee.tenant,
            employee=employee,
            work_date=work_date,
            defaults=defaults,
        )
        if shift:
            assignment.shift = shift
        if scheduled_check_in is not None:
            assignment.scheduled_check_in = scheduled_check_in
        if scheduled_check_out is not None:
            assignment.scheduled_check_out = scheduled_check_out
        elif shift and scheduled_check_in is None and scheduled_check_out is None:
            assignment.scheduled_check_in = shift.scheduled_check_in
            assignment.scheduled_check_out = shift.scheduled_check_out
        assignment.save()
        record.shift_assignment = assignment
        record.save(update_fields=["shift_assignment", "updated_at"])

    return recalculate_daily_timesheet(employee, work_date)
