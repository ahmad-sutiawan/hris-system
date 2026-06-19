"""Import karyawan dari export Excel Talenta (Employee Database)."""

from __future__ import annotations

import re
from datetime import date, datetime
from io import BytesIO

from django.db import transaction

from apps.core.models import Plant
from apps.employees.models import Employee
from apps.employees.services.mandatory_defaults import NA, apply_mandatory_defaults
from apps.employees.services.onboarding import provision_new_employee
from apps.organization.models import Department, JobLevel, JobPosition
from apps.organization.services.codes import (
    department_code_from_name,
    job_level_code_from_name,
    job_position_code_from_name,
)

from apps.employees.talenta_mapping import TALENTA_REQUIRED_IMPORT_COLUMNS
from apps.employees.services.talenta_master import resolve_talenta_masters_from_row

from apps.employees.talenta_vocabulary import (
    TALENTA_JOB_LEVEL_RANK,
    branch_plant_code,
    branch_type_from_excel_name,
    canonical_branch_name,
)


class ImportErrorRow(Exception):
    def __init__(self, row_num, message):
        self.row_num = row_num
        self.message = message
        super().__init__(f"Baris {row_num}: {message}")


def _normalize_text(value) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def _cell(row: dict, key: str, default: str = "") -> str:
    if key not in row:
        return default
    return _normalize_text(row[key])


def _cell_preserve(row: dict, key: str, default: str = "") -> str:
    """Nilai teks persis dari Excel (hanya trim ujung, spasi ganda dipertahankan)."""
    if key not in row:
        return default
    value = row[key]
    if value is None:
        return default
    return str(value).strip()


def _parse_date(value) -> date | None:
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _map_gender(value: str) -> str:
    mapping = {
        "male": Employee.Gender.MALE,
        "female": Employee.Gender.FEMALE,
        "laki-laki": Employee.Gender.MALE,
        "perempuan": Employee.Gender.FEMALE,
    }
    return mapping.get(value.lower(), Employee.Gender.NA)


def _map_marital_status(value: str) -> str:
    mapping = {
        "single": Employee.MaritalStatus.SINGLE,
        "married": Employee.MaritalStatus.MARRIED,
        "divorced": Employee.MaritalStatus.DIVORCED,
        "widower": Employee.MaritalStatus.WIDOWED,
        "widow": Employee.MaritalStatus.WIDOWED,
        "janda/duda": Employee.MaritalStatus.WIDOWED,
    }
    return mapping.get(value.lower(), Employee.MaritalStatus.NA)


def _map_employment(row: dict) -> tuple[str, str, str, date | None, date | None]:
    status_employee = _cell(row, "Status Employee") or "Permanent"
    status_text = status_employee.lower()
    resign_date = _parse_date(row.get("Resign Date"))
    contract_end = _parse_date(row.get("End Date"))

    if resign_date:
        return Employee.Status.RESIGNED, Employee.SalaryScheme.MONTHLY, status_employee, resign_date, contract_end

    if status_text == "contract":
        return Employee.Status.CONTRACT, Employee.SalaryScheme.MONTHLY, status_employee, None, contract_end

    if status_text == "harian":
        return Employee.Status.PERMANENT, Employee.SalaryScheme.DAILY, status_employee, None, contract_end

    return Employee.Status.PERMANENT, Employee.SalaryScheme.MONTHLY, status_employee, None, contract_end


def _load_rows(file_bytes: bytes) -> tuple[list[str], list[dict]]:
    try:
        import openpyxl
    except ImportError as exc:
        raise ValueError(
            "Paket openpyxl belum terpasang. Jalankan: pip install openpyxl"
        ) from exc

    workbook = openpyxl.load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)
    sheet = workbook.active
    rows_iter = sheet.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration as exc:
        raise ValueError("File Excel kosong.") from exc

    headers = [_normalize_text(h) for h in header_row]
    if not any(headers):
        raise ValueError("Header Excel tidak valid.")

    missing = [h for h in TALENTA_REQUIRED_IMPORT_COLUMNS if h not in headers]
    if missing:
        raise ValueError(f"Kolom wajib hilang: {', '.join(missing)}")

    rows = []
    for raw in rows_iter:
        if not any(cell is not None and str(cell).strip() for cell in raw):
            continue
        row = {headers[i]: raw[i] if i < len(raw) else None for i in range(len(headers))}
        rows.append(row)
    return headers, rows


class _OrgCache:
    def __init__(self, tenant):
        self.tenant = tenant
        self.plants: dict[str, Plant] = {}
        self.departments: dict[tuple[int, str], Department] = {}
        self.jobs: dict[tuple[int, str], JobPosition] = {}
        self.levels: dict[str, JobLevel] = {}
        self.pt_plants: dict[str, Plant] = {}
        self.master_cache: dict[tuple[str, str], object] = {}
        self.stats = {
            "plants_created": 0,
            "pt_plants_created": 0,
            "departments_created": 0,
            "job_positions_created": 0,
            "job_levels_created": 0,
            "talenta_masters_created": 0,
        }

    def get_pt_plant(self, parent_name: str) -> Plant | None:
        name = _normalize_text(parent_name)
        if not name:
            return None
        key = name.lower()
        if key in self.pt_plants:
            return self.pt_plants[key]

        from django.utils.text import slugify

        code = slugify(name).upper().replace("-", "_")[:20] or "PT"
        existing = Plant.objects.filter(
            tenant=self.tenant,
            entity_type=Plant.EntityType.PT,
            name=name,
        ).first()
        if not existing:
            existing = Plant.objects.filter(
                tenant=self.tenant,
                entity_type=Plant.EntityType.PT,
                code=code,
            ).first()
        if not existing:
            existing = Plant.objects.filter(tenant=self.tenant, code=code).first()
        if existing:
            if existing.entity_type != Plant.EntityType.PT:
                existing.entity_type = Plant.EntityType.PT
                existing.save(update_fields=["entity_type"])
            self.pt_plants[key] = existing
            return existing

        plant = Plant.objects.create(
            tenant=self.tenant,
            code=code,
            name=name,
            entity_type=Plant.EntityType.PT,
        )
        self.stats["pt_plants_created"] += 1
        self.pt_plants[key] = plant
        return plant

    def get_plant(self, branch_name: str, parent_branch_name: str = "") -> Plant:
        key = _normalize_text(branch_name).lower()
        if key in self.plants:
            return self.plants[key]

        name = canonical_branch_name(branch_name)
        code = branch_plant_code(name)
        branch_type = branch_type_from_excel_name(name)

        existing = Plant.objects.filter(
            tenant=self.tenant,
            entity_type=Plant.EntityType.BRANCH,
            name=name,
        ).first()
        if not existing:
            existing = Plant.objects.filter(
                tenant=self.tenant,
                entity_type=Plant.EntityType.BRANCH,
                code=code,
            ).first()
        if not existing:
            existing = Plant.objects.filter(tenant=self.tenant, code=code).first()

        if existing:
            updates = []
            parent = self.get_pt_plant(parent_branch_name) if parent_branch_name else None
            if parent and existing.parent_id != parent.pk and existing.pk != parent.pk:
                existing.parent = parent
                updates.append("parent")
            if existing.entity_type != Plant.EntityType.BRANCH:
                existing.entity_type = Plant.EntityType.BRANCH
                updates.append("entity_type")
            if existing.name != name:
                existing.name = name
                updates.append("name")
            if existing.branch_type != branch_type:
                existing.branch_type = branch_type
                updates.append("branch_type")
            if existing.code != code and not Plant.objects.filter(
                tenant=self.tenant, code=code
            ).exclude(pk=existing.pk).exists():
                existing.code = code
                updates.append("code")
            if updates:
                existing.save(update_fields=updates)
            self.plants[key] = existing
            return existing

        parent = self.get_pt_plant(parent_branch_name) if parent_branch_name else None
        plant = Plant.objects.create(
            tenant=self.tenant,
            code=code,
            name=name,
            branch_type=branch_type,
            entity_type=Plant.EntityType.BRANCH,
            parent=parent,
        )
        self.stats["plants_created"] += 1
        self.plants[key] = plant
        return plant

    def get_department(self, plant: Plant, org_name: str) -> Department:
        name = _cell_preserve({"Organization": org_name}, "Organization")
        key = (plant.pk, _normalize_text(name).lower())
        if key in self.departments:
            return self.departments[key]

        if not name:
            name = NA
        existing = Department.objects.filter(
            tenant=self.tenant, plant=plant, name=name
        ).first()
        if existing:
            self.departments[key] = existing
            return existing

        code = department_code_from_name(
            name,
            tenant_id=self.tenant.pk,
            plant_id=plant.pk,
        )
        dept = Department.objects.create(
            tenant=self.tenant,
            plant=plant,
            code=code,
            name=name,
        )
        self.stats["departments_created"] += 1
        self.departments[key] = dept
        return dept

    def get_job(self, plant: Plant, dept: Department, title: str) -> JobPosition:
        # Keyed by department too: a job position belongs to one department in
        # master data, so the same title under different organizations becomes
        # distinct positions (mis. QC Inspector di Melting vs Rolling Mills).
        key = (plant.pk, dept.pk, _normalize_text(title).lower())
        if key in self.jobs:
            return self.jobs[key]

        job_title = _normalize_text(title) or NA
        existing = JobPosition.objects.filter(
            tenant=self.tenant,
            plant=plant,
            department=dept,
            title=job_title,
        ).first()
        if existing:
            self.jobs[key] = existing
            return existing

        code = job_position_code_from_name(
            job_title,
            tenant_id=self.tenant.pk,
            plant_id=plant.pk,
        )
        job = JobPosition.objects.create(
            tenant=self.tenant,
            plant=plant,
            department=dept,
            code=code,
            title=job_title,
        )
        self.stats["job_positions_created"] += 1
        self.jobs[key] = job
        return job

    def get_job_level(self, level_name: str) -> JobLevel | None:
        name = _normalize_text(level_name)
        if not name:
            return None

        key = name.lower()
        if key in self.levels:
            return self.levels[key]

        existing = JobLevel.objects.filter(tenant=self.tenant, name=name).first()
        if existing:
            self.levels[key] = existing
            return existing

        code = job_level_code_from_name(name, tenant_id=self.tenant.pk)
        rank = TALENTA_JOB_LEVEL_RANK.get(key, 99)
        level = JobLevel.objects.create(
            tenant=self.tenant,
            code=code,
            name=name,
            rank=rank,
        )
        self.stats["job_levels_created"] += 1
        self.levels[key] = level
        return level


def _employee_defaults_from_row(row: dict, org: _OrgCache) -> dict:
    branch_name = _cell(row, "Branch Name") or _cell(row, "Parent Branch Name") or "Plant Utama"
    parent_name = _cell(row, "Parent Branch Name")
    plant = org.get_plant(branch_name, parent_name)
    dept = org.get_department(plant, _cell_preserve(row, "Organization") or NA)
    job = org.get_job(plant, dept, _cell(row, "Job Position") or NA)
    job_level = org.get_job_level(_cell(row, "Job Level"))

    masters = resolve_talenta_masters_from_row(org.tenant, row, cache=org.master_cache)

    join_date = _parse_date(row.get("Join Date"))
    if not join_date:
        raise ImportErrorRow(0, "Join Date wajib diisi.")

    status, salary_scheme, status_employee, resign_date, contract_end = _map_employment(row)

    phone = _cell(row, "Mobile Phone")
    phone_landline = _cell_preserve(row, "Phone")
    citizen_id_address = _cell_preserve(row, "Citizen ID Address")
    address = _cell_preserve(row, "Residential Address") or citizen_id_address
    nik = _cell(row, "NIK (NPWP 16 Digit)")
    npwp = _cell_preserve(row, "NPWP")
    npwp_16 = _cell(row, "NPWP 16 digit (new)") or nik

    tax_status_raw = _cell(row, "Employee Tax Status")
    tax_config_raw = _cell(row, "Tax Config")

    defaults = {
        "barcode": _cell(row, "Barcode"),
        "full_name": _cell(row, "Full Name") or NA,
        "nik": nik,
        "npwp_16_digit": npwp_16,
        "email": _cell(row, "Email"),
        "phone": phone,
        "phone_landline": phone_landline,
        "address": address,
        "citizen_id_address": citizen_id_address,
        "birth_place": _cell_preserve(row, "Birth Place"),
        "birth_date": _parse_date(row.get("Birth Date")),
        "talenta_age": _cell_preserve(row, "Age"),
        "gender": _map_gender(_cell(row, "Gender")),
        "marital_status": _map_marital_status(_cell(row, "Marital Status")),
        "plant": plant,
        "department": dept,
        "job_position": job,
        "job_level": job_level,
        "join_date": join_date,
        "sign_date": _parse_date(row.get("Sign Date")),
        "status": status,
        "status_employee": status_employee,
        "salary_scheme": salary_scheme,
        "length_of_service": _cell_preserve(row, "Length Of Service"),
        "tax_status": _cell(row, "PTKP Status"),
        "employee_tax_status": tax_status_raw,
        "tax_config": tax_config_raw,
        "npwp": npwp,
        "bank_name": _cell(row, "Bank Name"),
        "bank_account_number": _cell(row, "Bank Account"),
        "bank_account_name": _cell_preserve(row, "Bank Account Holder"),
        "bpjs_ketenagakerjaan_number": _cell(row, "BPJS Ketenagakerjaan"),
        "bpjs_kesehatan_number": _cell(row, "BPJS Kesehatan"),
        "passport_number": _cell(row, "Passport"),
        "passport_expiration_date": _parse_date(row.get("Passport Expiration Date")),
        "tax_ref_doc_type": _cell(row, "Jenis Dok. Referensi Bukti Potong"),
        "tax_ref_doc_number": _cell(row, "Nomor Dok. Referensi Bukti Potong"),
        "tax_ref_doc_date": _parse_date(row.get("Tanggal Dok. Referensi Bukti Potong")),
        "tin": _cell(row, "TIN (Taxpayer Identification Number)"),
        "profile_picture_url": _cell(row, "Profile Picture"),
        "religion": masters.get("religion"),
        "blood_type": masters.get("blood_type"),
        "nationality": masters.get("nationality"),
        "currency": masters.get("currency"),
        "payment_schedule": masters.get("payment_schedule"),
        "approval_line": masters.get("approval_line"),
        "grade": masters.get("grade"),
        "talenta_class": masters.get("employee_class"),
        "cost_center": masters.get("cost_center"),
        "cost_center_category": masters.get("cost_center_category"),
        "sbu": masters.get("sbu"),
        "employee_tax_status_master": masters.get("employee_tax_status"),
        "tax_config_master": masters.get("tax_config"),
    }

    if resign_date:
        defaults["resign_date"] = resign_date
    if contract_end:
        defaults["contract_end_date"] = contract_end

    return defaults


def _link_managers(tenant, rows: list[dict]) -> tuple[int, list[str]]:
    by_name = {
        emp.full_name.strip().lower(): emp
        for emp in Employee.objects.filter(tenant=tenant).only("pk", "full_name", "manager_id")
    }
    linked = 0
    warnings = []
    for row in rows:
        manager_name = _cell(row, "Manager")
        if not manager_name:
            continue
        employee_id = _cell(row, "Employee ID")
        employee = Employee.objects.filter(tenant=tenant, employee_id=employee_id).first()
        if not employee:
            continue
        manager = by_name.get(manager_name.lower())
        if not manager:
            warnings.append(f"Atasan '{manager_name}' tidak ditemukan untuk {employee.full_name}.")
            continue
        if manager.pk == employee.pk:
            continue
        if employee.manager_id != manager.pk:
            employee.manager = manager
            employee.save(update_fields=["manager"])
            linked += 1
    return linked, warnings


@transaction.atomic
def import_employees_talenta_xlsx(tenant, file_bytes: bytes, *, dry_run=False):
    _, rows = _load_rows(file_bytes)
    if not rows:
        raise ValueError("Tidak ada baris data karyawan.")

    org = _OrgCache(tenant)
    created = 0
    updated = 0
    errors: list[str] = []

    for row_num, row in enumerate(rows, start=2):
        try:
            employee_id = _cell(row, "Employee ID")
            if not employee_id:
                raise ImportErrorRow(row_num, "Employee ID wajib diisi.")
            if not _cell(row, "Full Name"):
                raise ImportErrorRow(row_num, "Full Name wajib diisi.")

            defaults = _employee_defaults_from_row(row, org)

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
            apply_mandatory_defaults(obj, fill_fk=False, skip_na_fill=True)
            obj.save()
            if was_created:
                created += 1
                provision_new_employee(obj, assign_shift=True, sync_credentials=True)
            else:
                updated += 1
        except ImportErrorRow as exc:
            errors.append(str(exc).replace("Baris 0:", f"Baris {row_num}:"))
        except Exception as exc:
            errors.append(f"Baris {row_num}: {exc}")

    managers_linked = 0
    manager_warnings: list[str] = []
    if not dry_run:
        managers_linked, manager_warnings = _link_managers(tenant, rows)

    return {
        "created": created,
        "updated": updated,
        "errors": errors,
        "managers_linked": managers_linked,
        "manager_warnings": manager_warnings[:20],
        **org.stats,
    }
