import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import StringIO

from django.db import transaction

from apps.core.models import Plant
from apps.employees.models import Employee
from apps.organization.models import Department, JobPosition

IMPORT_HEADERS = [
    "employee_id",
    "full_name",
    "nik",
    "email",
    "phone",
    "plant_code",
    "department_code",
    "job_code",
    "join_date",
    "status",
    "base_salary",
    "allowance_transport",
    "tax_status",
    "bank_name",
    "bank_account_number",
    "bank_account_name",
    "npwp",
]


class ImportErrorRow(Exception):
    def __init__(self, row_num, message):
        self.row_num = row_num
        self.message = message
        super().__init__(f"Baris {row_num}: {message}")


def template_csv():
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(IMPORT_HEADERS)
    writer.writerow(
        [
            "PLT01-2026-002",
            "Siti Aminah",
            "3201010101900002",
            "siti@demo.local",
            "08123456789",
            "PLT01",
            "PROD",
            "OPR",
            "2026-01-15",
            "permanent",
            "4500000",
            "500000",
            "TK/0",
            "BCA",
            "1234567890",
            "Siti Aminah",
            "",
        ]
    )
    return buffer.getvalue()


def _parse_decimal(value, default="0"):
    try:
        return Decimal(str(value or default))
    except (InvalidOperation, TypeError):
        return Decimal(default)


def _parse_date(value):
    if not value or not str(value).strip():
        return None
    return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()


@transaction.atomic
def import_employees_csv(tenant, file_content, *, dry_run=False):
    reader = csv.DictReader(StringIO(file_content))
    if not reader.fieldnames:
        raise ValueError("File CSV kosong atau header tidak valid.")

    missing = set(IMPORT_HEADERS) - set(reader.fieldnames)
    if missing:
        raise ValueError(f"Kolom wajib hilang: {', '.join(sorted(missing))}")

    plants = {p.code: p for p in Plant.objects.filter(tenant=tenant)}
    departments = {
        (d.plant.code, d.code): d
        for d in Department.objects.filter(tenant=tenant).select_related("plant")
    }
    jobs = {
        (j.plant.code, j.code): j
        for j in JobPosition.objects.filter(tenant=tenant).select_related("plant")
    }

    created = 0
    updated = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):
        try:
            plant_code = row["plant_code"].strip()
            plant = plants.get(plant_code)
            if not plant:
                raise ImportErrorRow(row_num, f"Plant '{plant_code}' tidak ditemukan.")

            dept = departments.get((plant_code, row["department_code"].strip()))
            job = jobs.get((plant_code, row["job_code"].strip()))

            employee_id = row["employee_id"].strip()
            if not employee_id:
                raise ImportErrorRow(row_num, "employee_id wajib diisi.")

            defaults = {
                "full_name": row["full_name"].strip(),
                "nik": row["nik"].strip(),
                "email": row["email"].strip(),
                "phone": row["phone"].strip(),
                "plant": plant,
                "department": dept,
                "job_position": job,
                "join_date": _parse_date(row["join_date"]),
                "status": row["status"].strip() or Employee.Status.PERMANENT,
                "base_salary": _parse_decimal(row["base_salary"]),
                "allowance_transport": _parse_decimal(row["allowance_transport"]),
                "tax_status": row["tax_status"].strip(),
                "bank_name": row["bank_name"].strip(),
                "bank_account_number": row["bank_account_number"].strip(),
                "bank_account_name": row["bank_account_name"].strip(),
                "npwp": row["npwp"].strip(),
            }

            if dry_run:
                if Employee.objects.filter(tenant=tenant, employee_id=employee_id).exists():
                    updated += 1
                else:
                    created += 1
                continue

            obj, was_created = Employee.objects.update_or_create(
                tenant=tenant,
                employee_id=employee_id,
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1
        except ImportErrorRow as exc:
            errors.append(str(exc))
        except Exception as exc:
            errors.append(f"Baris {row_num}: {exc}")

    return {"created": created, "updated": updated, "errors": errors}
