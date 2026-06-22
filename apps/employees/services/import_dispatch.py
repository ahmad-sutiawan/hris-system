"""Deteksi format file import karyawan (template HRIS vs export Talenta)."""

from __future__ import annotations

from apps.core.xlsx_io import read_xlsx_rows
from apps.employees.services.import_csv import import_employees_xlsx
from apps.employees.services.import_talenta import import_employees_talenta_xlsx
from apps.employees.talenta_mapping import TALENTA_EMPLOYEE_COLUMNS


def _is_talenta_headers(headers: list[str]) -> bool:
    normalized = {str(h).strip() for h in headers if h}
    return "Employee ID" in normalized and "Full Name" in normalized


def import_employees_file(tenant, *, filename: str, content: bytes, dry_run=False):
    name = (filename or "").lower()
    if name.endswith(".csv"):
        from apps.employees.services.import_csv import import_employees_csv

        text = content.decode("utf-8-sig")
        return import_employees_csv(tenant, text, dry_run=dry_run)

    if not (name.endswith(".xlsx") or name.endswith(".xlsm")):
        raise ValueError("Format file tidak didukung. Gunakan .xlsx (template HRIS atau export Talenta).")

    headers, _ = read_xlsx_rows(content)
    if _is_talenta_headers(headers):
        return import_employees_talenta_xlsx(tenant, content, dry_run=dry_run)
    return import_employees_xlsx(tenant, content, dry_run=dry_run)
