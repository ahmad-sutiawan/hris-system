import csv
from datetime import datetime
from io import StringIO

from django.db import transaction
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.attendance.services.timesheet import recalculate_daily_timesheet
from apps.employees.models import Employee


IMPORT_HEADERS = [
    "employee_id",
    "work_date",
    "check_in",
    "check_out",
    "device_id",
]


class PunchImportError(Exception):
    pass


def template_csv() -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(IMPORT_HEADERS)
    writer.writerow(
        [
            "PLT01-2026-001",
            "2026-06-01",
            "2026-06-01 07:02:00",
            "2026-06-01 15:05:00",
            "FP-01",
        ]
    )
    return buffer.getvalue()


def _parse_dt(value: str):
    if not value or not str(value).strip():
        return None
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S"):
        try:
            dt = datetime.strptime(raw, fmt)
            return timezone.make_aware(dt, timezone.get_current_timezone())
        except ValueError:
            continue
    raise PunchImportError(f"Format datetime tidak dikenali: {raw}")


@transaction.atomic
def import_attendance_csv(tenant, file_content: str, *, plant=None) -> dict:
    reader = csv.DictReader(StringIO(file_content))
    if not reader.fieldnames:
        raise PunchImportError("CSV kosong atau header tidak valid.")

    missing = set(IMPORT_HEADERS) - set(reader.fieldnames)
    if missing:
        raise PunchImportError(f"Kolom wajib hilang: {', '.join(sorted(missing))}")

    employees = {
        e.employee_id: e
        for e in Employee.objects.filter(tenant=tenant).select_related("plant")
    }

    created = 0
    updated = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):
        try:
            employee_id = row["employee_id"].strip()
            employee = employees.get(employee_id)
            if not employee:
                raise PunchImportError(f"Karyawan '{employee_id}' tidak ditemukan.")

            if plant and employee.plant_id != plant.id:
                raise PunchImportError(f"Karyawan '{employee_id}' bukan plant ini.")

            work_date = datetime.strptime(row["work_date"].strip(), "%Y-%m-%d").date()
            check_in = _parse_dt(row.get("check_in", ""))
            check_out = _parse_dt(row.get("check_out", ""))
            device_id = row.get("device_id", "").strip()
            notes = f"Import fingerprint {device_id}" if device_id else "Import fingerprint"

            record, was_created = AttendanceRecord.objects.update_or_create(
                employee=employee,
                work_date=work_date,
                defaults={
                    "tenant": tenant,
                    "plant": employee.plant,
                    "check_in": check_in,
                    "check_out": check_out,
                    "source": AttendanceRecord.Source.IMPORT,
                    "notes": notes,
                },
            )
            recalculate_daily_timesheet(employee, work_date)
            if was_created:
                created += 1
            else:
                updated += 1
        except PunchImportError as exc:
            errors.append(f"Baris {row_num}: {exc}")
        except Exception as exc:
            errors.append(f"Baris {row_num}: {exc}")

    return {"created": created, "updated": updated, "errors": errors}
