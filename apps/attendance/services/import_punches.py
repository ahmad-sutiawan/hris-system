from datetime import datetime

from django.db import transaction
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.attendance.services.timesheet import recalculate_daily_timesheet
from apps.core.xlsx_io import read_xlsx_rows, write_xlsx
from apps.employees.models import Employee

IMPORT_HEADERS = [
    "employee_id",
    "work_date",
    "check_in",
    "check_out",
    "device_id",
    "notes",
    "source",
]


class PunchImportError(Exception):
    pass


def template_xlsx() -> bytes:
    return write_xlsx(
        IMPORT_HEADERS,
        [
            [
                "PLT01-2026-001",
                "2026-06-01",
                "2026-06-01 07:02:00",
                "2026-06-01 15:05:00",
                "FP-01",
                "Import fingerprint",
                "import",
            ]
        ],
    )


template_csv = template_xlsx


def _parse_dt(value: str):
    if not value or not str(value).strip():
        return None
    raw = str(value).strip()
    if "T" in raw:
        raw = raw.replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S"):
        try:
            dt = datetime.strptime(raw, fmt)
            return timezone.make_aware(dt, timezone.get_current_timezone())
        except ValueError:
            continue
    raise PunchImportError(f"Format datetime tidak dikenali: {raw}")


def _parse_date(value):
    raw = str(value).strip()
    if " " in raw:
        raw = raw.split(" ", 1)[0]
    return datetime.strptime(raw, "%Y-%m-%d").date()


@transaction.atomic
def import_attendance_rows(tenant, rows, *, plant=None) -> dict:
    if not rows:
        raise PunchImportError("File Excel kosong atau tidak ada baris data.")

    fieldnames = list(rows[0].keys())
    missing = set(IMPORT_HEADERS[:5]) - set(fieldnames)
    if missing:
        raise PunchImportError(f"Kolom wajib hilang: {', '.join(sorted(missing))}")

    employees = {
        e.employee_id: e
        for e in Employee.objects.filter(tenant=tenant).select_related("plant")
    }

    created = 0
    updated = 0
    errors = []

    for row_num, row in enumerate(rows, start=2):
        try:
            employee_id = str(row["employee_id"]).strip()
            employee = employees.get(employee_id)
            if not employee:
                raise PunchImportError(f"Karyawan '{employee_id}' tidak ditemukan.")

            if plant and employee.plant_id != plant.id:
                raise PunchImportError(f"Karyawan '{employee_id}' bukan plant ini.")

            work_date = _parse_date(row["work_date"])
            check_in = _parse_dt(row.get("check_in", ""))
            check_out = _parse_dt(row.get("check_out", ""))
            device_id = str(row.get("device_id", "") or "").strip()
            notes = str(row.get("notes", "") or "").strip()
            if not notes:
                notes = f"Import fingerprint {device_id}" if device_id else "Import fingerprint"
            source = str(row.get("source", "") or AttendanceRecord.Source.IMPORT).strip().lower()
            if source not in AttendanceRecord.Source.values:
                source = AttendanceRecord.Source.IMPORT

            record, was_created = AttendanceRecord.objects.update_or_create(
                employee=employee,
                work_date=work_date,
                defaults={
                    "tenant": tenant,
                    "plant": employee.plant,
                    "check_in": check_in,
                    "check_out": check_out,
                    "source": source,
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


@transaction.atomic
def import_attendance_xlsx(tenant, file_bytes: bytes, *, plant=None) -> dict:
    _, rows = read_xlsx_rows(file_bytes)
    return import_attendance_rows(tenant, rows, plant=plant)


def import_attendance_csv(tenant, file_content: str, *, plant=None) -> dict:
    import csv
    from io import StringIO

    reader = csv.DictReader(StringIO(file_content))
    if not reader.fieldnames:
        raise PunchImportError("File kosong atau header tidak valid.")
    return import_attendance_rows(tenant, list(reader), plant=plant)
