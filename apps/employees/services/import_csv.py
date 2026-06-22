from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction

from apps.core.models import Plant
from apps.core.xlsx_io import read_xlsx_rows, write_xlsx
from apps.employees.models import Employee
from apps.employees.services.mandatory_defaults import NA, apply_mandatory_defaults
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
    "gender",
    "marital_status",
    "birth_place",
    "birth_date",
    "address",
    "mother_name",
    "job_level_code",
    "barcode",
    "phone_landline",
    "citizen_id_address",
    "sign_date",
    "contract_end_date",
    "resign_date",
    "status_employee",
    "employee_tax_status",
    "tax_config",
    "pph21_deduct",
]

IMPORT_HEADERS = REQUIRED_HEADERS + OPTIONAL_HEADERS


class ImportErrorRow(Exception):
    def __init__(self, row_num, message):
        self.row_num = row_num
        self.message = message
        super().__init__(f"Baris {row_num}: {message}")


def template_xlsx() -> bytes:
    return write_xlsx(
        IMPORT_HEADERS,
        [
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
                "123456789012345",
                "daily",
                "25000",
                "0",
                "0001234567890",
                "12345678901",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ]
        ],
    )


template_csv = template_xlsx


def _parse_decimal(value, default="0"):
    try:
        return Decimal(str(value or default))
    except (InvalidOperation, TypeError):
        return Decimal(default)


def _parse_date(value):
    if not value or not str(value).strip():
        return None
    raw = str(value).strip()
    if " " in raw:
        raw = raw.split(" ", 1)[0]
    return datetime.strptime(raw, "%Y-%m-%d").date()


def _row_value(row, key, default=""):
    if key not in row:
        return default
    value = row[key]
    if value is None:
        return default
    return value


@transaction.atomic
def import_employee_rows(tenant, rows, *, dry_run=False):
    if not rows:
        raise ValueError("File Excel kosong atau tidak ada baris data.")

    first = rows[0]
    fieldnames = list(first.keys())
    missing = set(REQUIRED_HEADERS) - set(fieldnames)
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
    from apps.organization.models import JobLevel

    job_levels = {jl.code: jl for jl in JobLevel.objects.filter(tenant=tenant)}

    created = 0
    updated = 0
    errors = []

    for row_num, row in enumerate(rows, start=2):
        try:
            plant_code = str(row["plant_code"]).strip()
            plant = plants.get(plant_code)
            if not plant:
                raise ImportErrorRow(row_num, f"Plant '{plant_code}' tidak ditemukan.")

            dept = departments.get((plant_code, str(row["department_code"]).strip()))
            job = jobs.get((plant_code, str(row["job_code"]).strip()))

            employee_id = str(row["employee_id"]).strip()
            if not employee_id:
                raise ImportErrorRow(row_num, "employee_id wajib diisi.")

            full_name = str(row["full_name"]).strip()
            nik = str(row["nik"]).strip() or NA
            email = str(row["email"]).strip() or NA
            phone = str(row["phone"]).strip() or NA
            if not full_name:
                raise ImportErrorRow(row_num, "full_name wajib diisi.")
            if not dept:
                raise ImportErrorRow(row_num, "department_code tidak valid.")
            if not job:
                raise ImportErrorRow(row_num, "job_code tidak valid.")
            join_date = _parse_date(row["join_date"])
            if not join_date:
                raise ImportErrorRow(row_num, "join_date wajib diisi (YYYY-MM-DD).")
            tax_status = str(row["tax_status"]).strip() or NA

            gender = str(_row_value(row, "gender")).strip() or Employee.Gender.NA
            marital_status = str(_row_value(row, "marital_status")).strip() or Employee.MaritalStatus.NA
            birth_place = str(_row_value(row, "birth_place")).strip() or NA
            birth_date = _parse_date(_row_value(row, "birth_date"))
            address = str(_row_value(row, "address")).strip() or NA
            mother_name = str(_row_value(row, "mother_name")).strip() or NA
            if gender not in Employee.Gender.values:
                raise ImportErrorRow(row_num, f"gender '{gender}' tidak valid.")
            if marital_status not in Employee.MaritalStatus.values:
                raise ImportErrorRow(row_num, f"marital_status '{marital_status}' tidak valid.")

            job_level_code = str(_row_value(row, "job_level_code")).strip()
            job_level = job_levels.get(job_level_code) if job_level_code else None
            if job_level_code and not job_level:
                raise ImportErrorRow(row_num, f"job_level_code '{job_level_code}' tidak ditemukan.")

            salary_scheme = str(_row_value(row, "salary_scheme", Employee.SalaryScheme.MONTHLY)).strip()
            if salary_scheme and salary_scheme not in Employee.SalaryScheme.values:
                raise ImportErrorRow(
                    row_num,
                    f"salary_scheme '{salary_scheme}' tidak valid (monthly/daily).",
                )

            defaults = {
                "full_name": full_name,
                "nik": nik,
                "email": email,
                "phone": phone,
                "phone_landline": str(_row_value(row, "phone_landline")).strip() or "",
                "plant": plant,
                "department": dept,
                "job_position": job,
                "job_level": job_level,
                "join_date": join_date,
                "sign_date": _parse_date(_row_value(row, "sign_date")),
                "contract_end_date": _parse_date(_row_value(row, "contract_end_date")),
                "resign_date": _parse_date(_row_value(row, "resign_date")),
                "status_employee": str(_row_value(row, "status_employee")).strip(),
                "status": str(row["status"]).strip() or Employee.Status.PERMANENT,
                "salary_scheme": salary_scheme or Employee.SalaryScheme.MONTHLY,
                "base_salary": _parse_decimal(row["base_salary"]),
                "allowance_transport": _parse_decimal(row["allowance_transport"]),
                "allowance_meal": _parse_decimal(_row_value(row, "allowance_meal")),
                "allowance_position": _parse_decimal(_row_value(row, "allowance_position")),
                "tax_status": tax_status,
                "employee_tax_status": str(_row_value(row, "employee_tax_status")).strip() or "",
                "tax_config": str(_row_value(row, "tax_config")).strip() or "",
                "bank_name": str(row["bank_name"]).strip() or NA,
                "bank_account_number": str(row["bank_account_number"]).strip() or NA,
                "bank_account_name": str(row["bank_account_name"]).strip() or NA,
                "npwp": str(row["npwp"]).strip() or NA,
                "bpjs_kesehatan_number": str(_row_value(row, "bpjs_kesehatan_number")).strip() or NA,
                "bpjs_ketenagakerjaan_number": str(
                    _row_value(row, "bpjs_ketenagakerjaan_number")
                ).strip()
                or NA,
                "gender": gender,
                "marital_status": marital_status,
                "birth_place": birth_place,
                "birth_date": birth_date,
                "address": address,
                "citizen_id_address": str(_row_value(row, "citizen_id_address")).strip() or "",
                "mother_name": mother_name,
                "barcode": str(_row_value(row, "barcode")).strip(),
            }
            pph21 = _row_value(row, "pph21_deduct")
            if pph21 not in (None, ""):
                defaults["pph21_deduct"] = str(pph21).strip().lower() in {"1", "true", "yes"}

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
            apply_mandatory_defaults(obj, fill_fk=True)
            obj.save()
            if was_created:
                created += 1
                provision_new_employee(obj, assign_shift=True, sync_credentials=True)
            else:
                updated += 1
        except ImportErrorRow as exc:
            errors.append(str(exc))
        except Exception as exc:
            errors.append(f"Baris {row_num}: {exc}")

    return {"created": created, "updated": updated, "errors": errors}


@transaction.atomic
def import_employees_xlsx(tenant, file_bytes: bytes, *, dry_run=False):
    _, rows = read_xlsx_rows(file_bytes)
    return import_employee_rows(tenant, rows, dry_run=dry_run)


def import_employees_csv(tenant, file_content, *, dry_run=False):
    import csv
    from io import StringIO

    reader = csv.DictReader(StringIO(file_content))
    if not reader.fieldnames:
        raise ValueError("File kosong atau header tidak valid.")
    return import_employee_rows(tenant, list(reader), dry_run=dry_run)
