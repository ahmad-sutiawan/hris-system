from datetime import date

from django.core.files.base import ContentFile
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


def _save_photo(record: AttendanceRecord, field_name: str, photo: ContentFile):
    current = getattr(record, field_name)
    if current:
        current.delete(save=False)
    setattr(record, field_name, photo)
    record.save(update_fields=[field_name, "updated_at"])


@transaction.atomic
def clock_in(
    employee: Employee,
    *,
    source=AttendanceRecord.Source.WEB,
    when=None,
    photo: ContentFile | None = None,
    latitude=None,
    longitude=None,
    notes: str = "",
):
    if not photo:
        raise PunchError("Foto selfie wajib untuk clock in.")

    when = when or timezone.now()
    work_date = timezone.localdate(when)

    record, _created = AttendanceRecord.objects.get_or_create(
        employee=employee,
        work_date=work_date,
        defaults={
            "tenant": employee.tenant,
            "plant": employee.plant,
            "check_in": when,
            "source": source,
        },
    )

    record.check_in = when
    record.check_out = None
    record.source = source
    if latitude is not None:
        record.latitude = latitude
    if longitude is not None:
        record.longitude = longitude
    if notes:
        record.notes = notes

    assignment = _get_assignment(employee, work_date)
    if assignment:
        record.shift_assignment = assignment

    record.save()
    _save_photo(record, "check_in_photo", photo)
    recalculate_daily_timesheet(employee, work_date)
    return record


@transaction.atomic
def clock_out(
    employee: Employee,
    *,
    when=None,
    photo: ContentFile | None = None,
    latitude=None,
    longitude=None,
    notes: str = "",
):
    if not photo:
        raise PunchError("Foto selfie wajib untuk clock out.")

    when = when or timezone.now()
    work_date = timezone.localdate(when)

    record, created = AttendanceRecord.objects.get_or_create(
        employee=employee,
        work_date=work_date,
        defaults={
            "tenant": employee.tenant,
            "plant": employee.plant,
            "check_in": when,
            "source": AttendanceRecord.Source.WEB,
        },
    )

    if not record.check_in:
        record.check_in = when

    record.check_out = when
    if latitude is not None:
        record.latitude = latitude
    if longitude is not None:
        record.longitude = longitude
    if notes:
        record.notes = notes
    record.save(update_fields=[
        "check_in",
        "check_out",
        "latitude",
        "longitude",
        "notes",
        "updated_at",
    ])
    _save_photo(record, "check_out_photo", photo)
    recalculate_daily_timesheet(employee, work_date)
    return record
