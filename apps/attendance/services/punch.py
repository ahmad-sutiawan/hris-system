from datetime import date

from django.db import transaction
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.attendance.services.timesheet import recalculate_daily_timesheet
from apps.employees.models import Employee
from apps.shifts.models import ShiftAssignment


class PunchError(Exception):
    pass


def _today():
    return timezone.localdate()


def _get_assignment(employee: Employee, work_date: date):
    return ShiftAssignment.objects.filter(
        employee=employee,
        work_date=work_date,
    ).first()


@transaction.atomic
def clock_in(
    employee: Employee,
    *,
    source=AttendanceRecord.Source.WEB,
    when=None,
):
    when = when or timezone.now()
    work_date = timezone.localdate(when)

    record, created = AttendanceRecord.objects.get_or_create(
        employee=employee,
        work_date=work_date,
        defaults={
            "tenant": employee.tenant,
            "plant": employee.plant,
            "check_in": when,
            "source": source,
        },
    )
    if not created:
        if record.check_in and not record.check_out:
            raise PunchError("Sudah clock in hari ini.")
        record.check_in = when
        record.check_out = None
        record.source = source
        record.save(update_fields=["check_in", "check_out", "source", "updated_at"])

    assignment = _get_assignment(employee, work_date)
    if assignment:
        record.shift_assignment = assignment
        record.save(update_fields=["shift_assignment", "updated_at"])

    recalculate_daily_timesheet(employee, work_date)
    return record


@transaction.atomic
def clock_out(employee: Employee, *, when=None):
    when = when or timezone.now()
    work_date = timezone.localdate(when)

    try:
        record = AttendanceRecord.objects.get(employee=employee, work_date=work_date)
    except AttendanceRecord.DoesNotExist as exc:
        raise PunchError("Belum clock in hari ini.") from exc

    if not record.check_in:
        raise PunchError("Belum clock in hari ini.")
    if record.check_out:
        raise PunchError("Sudah clock out hari ini.")

    record.check_out = when
    record.save(update_fields=["check_out", "updated_at"])
    recalculate_daily_timesheet(employee, work_date)
    return record
