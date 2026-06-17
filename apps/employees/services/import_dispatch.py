"""Deteksi format file import karyawan (CSV internal vs Excel Talenta)."""

from __future__ import annotations

from apps.employees.services.import_csv import import_employees_csv
from apps.employees.services.import_talenta import import_employees_talenta_xlsx


def import_employees_file(tenant, *, filename: str, content: bytes, dry_run=False):
    name = (filename or "").lower()
    if name.endswith(".xlsx") or name.endswith(".xlsm"):
        return import_employees_talenta_xlsx(tenant, content, dry_run=dry_run)
    if name.endswith(".csv"):
        text = content.decode("utf-8-sig")
        return import_employees_csv(tenant, text, dry_run=dry_run)
    raise ValueError("Format file tidak didukung. Gunakan CSV (template HRIS) atau XLSX (export Talenta).")
