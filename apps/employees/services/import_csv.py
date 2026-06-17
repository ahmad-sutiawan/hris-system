import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import StringIO

from django.db import transaction

from apps.core.models import Plant
from apps.employees.models import Employee
from apps.employees.services.onboarding import provision_new_employee
from apps.organization.models import Department, JobPosition

REQUIRED_HEADERS = [
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

OPTIONAL_HEADERS = [
    "salary_scheme",
    "allowance_meal",
    "allowance_position",
    "bpjs_kesehatan_number",
    "bpjs_ketenagakerjaan_number",
]

IMPORT_HEADERS = REQUIRED_HEADERS + OPTIONAL_HEADERS


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
            "200000",
            "50000",
            "TK/0",
            "BCA",
            "1234567890",
            "Siti Aminah",
            "",
            "daily",
            "25000",
            "0",
            "0001234567890",
            "12345678901",
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


def _row_value(row, key, default=""):
    if key not in row:
        return default
    return row[key]


@transaction.atomic
def import_employees_csv(tenant, file_content, *, dry_run=False):
    reader = csv.DictReader(StringIO(file_content))
    if not reader.fieldnames:
        raise ValueError("File CSV kosong atau header tidak valid.")

    missing = set(REQUIRED_HEADERS) - set(reader.fieldnames)
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

            salary_scheme = _row_value(row, "salary_scheme", Employee.SalaryScheme.MONTHLY).strip()
            if salary_scheme and salary_scheme not in Employee.SalaryScheme.values:
                raise ImportErrorRow(
                    row_num,
                    f"salary_scheme '{salary_scheme}' tidak valid (monthly/daily).",
                )

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
                "salary_scheme": salary_scheme or Employee.SalaryScheme.MONTHLY,
                "base_salary": _parse_decimal(row["base_salary"]),
                "allowance_transport": _parse_decimal(row["allowance_transport"]),
                "allowance_meal": _parse_decimal(_row_value(row, "allowance_meal")),
                "allowance_position": _parse_decimal(_row_value(row, "allowance_position")),
                "tax_status": row["tax_status"].strip(),
                "bank_name": row["bank_name"].strip(),
                "bank_account_number": row["bank_account_number"].strip(),
                "bank_account_name": row["bank_account_name"].strip(),
                "npwp": row["npwp"].strip(),
                "bpjs_kesehatan_number": _row_value(row, "bpjs_kesehatan_number").strip(),
                "bpjs_ketenagakerjaan_number": _row_value(
                    row, "bpjs_ketenagakerjaan_number"
                ).strip(),
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
                provision_new_employee(obj, assign_shift=True)
            else:
                updated += 1
        except ImportErrorRow as exc:
            errors.append(str(exc))
        except Exception as exc:
            errors.append(f"Baris {row_num}: {exc}")

    return {"created": created, "updated": updated, "errors": errors}
