from datetime import date

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.attendance.models import AttendancePunch, AttendanceRecord
from apps.attendance.services.face_check import FaceCheckError, validate_selfie_face
from apps.attendance.services.geo import GeoFenceError, validate_punch_location
from apps.attendance.services.punch_recalc import schedule_daily_timesheet_recalc
from apps.attendance.services.punch_work_date import resolve_punch_work_date
from apps.employees.models import Employee
from apps.shifts.models import ShiftAssignment


class PunchError(Exception):
    pass


def _get_assignment(employee: Employee, work_date: date):
    return ShiftAssignment.objects.filter(
        employee=employee,
        work_date=work_date,
    ).select_related("shift").first()


def _normalize_photo(photo: ContentFile) -> ContentFile:
    if hasattr(photo, "seek"):
        photo.seek(0)
    data = photo.read()
    if not data:
        raise PunchError("Foto selfie wajib untuk absensi.")
    name = getattr(photo, "name", "selfie.jpg")
    return ContentFile(data, name=name)


def _validate_punch_inputs(
    employee: Employee,
    *,
    photo: ContentFile,
    source,
    latitude=None,
    longitude=None,
) -> ContentFile:
    photo = _normalize_photo(photo)
    try:
        validate_selfie_face(photo, employee=employee)
    except FaceCheckError as exc:
        raise PunchError(str(exc)) from exc
    photo.seek(0)
    if source == AttendanceRecord.Source.MOBILE:
        try:
            validate_punch_location(employee, latitude, longitude)
        except GeoFenceError as exc:
            raise PunchError(str(exc)) from exc
    return photo


def _save_punch_photo(punch: AttendancePunch, photo: ContentFile) -> None:
    photo.seek(0)
    punch.photo.save(photo.name, photo, save=True)


def _create_punch(
    record: AttendanceRecord,
    *,
    punch_type: str,
    when,
    photo: ContentFile,
    source,
    latitude=None,
    longitude=None,
    notes: str = "",
) -> AttendancePunch:
    punch = AttendancePunch.objects.create(
        tenant=record.tenant,
        attendance_record=record,
        employee=record.employee,
        work_date=record.work_date,
        punch_type=punch_type,
        punched_at=when,
        source=source,
        latitude=latitude,
        longitude=longitude,
        notes=notes,
    )
    _save_punch_photo(punch, photo)
    return punch


def sync_record_summary(record: AttendanceRecord) -> AttendanceRecord:
    """Derive summary CI/CO on the daily record from all punch events."""
    punches = list(record.punches.order_by("punched_at", "pk"))
    ins = [p for p in punches if p.punch_type == AttendancePunch.PunchType.IN]
    outs = [p for p in punches if p.punch_type == AttendancePunch.PunchType.OUT]

    update_fields = ["updated_at"]
    if ins:
        earliest_in = ins[0].punched_at
        if record.check_in != earliest_in:
            record.check_in = earliest_in
            update_fields.append("check_in")
        latest_in_photo = ins[-1].photo
        if latest_in_photo and latest_in_photo.name:
            if not record.check_in_photo or record.check_in_photo.name != latest_in_photo.name:
                record.check_in_photo = latest_in_photo
                update_fields.append("check_in_photo")
    if outs:
        latest_out = outs[-1].punched_at
        if record.check_out != latest_out:
            record.check_out = latest_out
            update_fields.append("check_out")
        latest_out_photo = outs[-1].photo
        if latest_out_photo and latest_out_photo.name:
            if not record.check_out_photo or record.check_out_photo.name != latest_out_photo.name:
                record.check_out_photo = latest_out_photo
                update_fields.append("check_out_photo")

    if len(update_fields) > 1:
        record.save(update_fields=update_fields)
    return record


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

    photo = _validate_punch_inputs(
        employee,
        photo=photo,
        source=source,
        latitude=latitude,
        longitude=longitude,
    )

    when = when or timezone.now()
    work_date = resolve_punch_work_date(employee, when, is_clock_out=False)

    with transaction.atomic():
        record, _created = AttendanceRecord.objects.get_or_create(
            employee=employee,
            work_date=work_date,
            defaults={
                "tenant": employee.tenant,
                "plant": employee.plant,
                "source": source,
            },
        )

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

        _create_punch(
            record,
            punch_type=AttendancePunch.PunchType.IN,
            when=when,
            photo=photo,
            source=source,
            latitude=latitude,
            longitude=longitude,
            notes=notes,
        )
        sync_record_summary(record)

    schedule_daily_timesheet_recalc(employee.pk, work_date)
    return record


def clock_out(
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
        raise PunchError("Foto selfie wajib untuk clock out.")

    photo = _validate_punch_inputs(
        employee,
        photo=photo,
        source=source,
        latitude=latitude,
        longitude=longitude,
    )

    when = when or timezone.now()
    work_date = resolve_punch_work_date(employee, when, is_clock_out=True)

    with transaction.atomic():
        record = (
            AttendanceRecord.objects.select_for_update()
            .filter(employee=employee, work_date=work_date)
            .first()
        )

        if not record:
            record = AttendanceRecord.objects.create(
                tenant=employee.tenant,
                employee=employee,
                plant=employee.plant,
                work_date=work_date,
                source=source,
            )

        if latitude is not None:
            record.latitude = latitude
        if longitude is not None:
            record.longitude = longitude
        if notes:
            record.notes = notes
        record.save()

        _create_punch(
            record,
            punch_type=AttendancePunch.PunchType.OUT,
            when=when,
            photo=photo,
            source=source,
            latitude=latitude,
            longitude=longitude,
            notes=notes,
        )
        sync_record_summary(record)

    schedule_daily_timesheet_recalc(employee.pk, work_date)
    return record
