"""Indeks identitas karyawan untuk impor sisipan."""

from __future__ import annotations

from apps.employees.models import Employee
from apps.employees.nik_lookup import compute_nik_lookup

_PLACEHOLDER_NIK = {"", "n/a", "na", "-"}


def normalize_person_name(value: str) -> str:
    return " ".join((value or "").split()).casefold()


def is_real_nik(value: str) -> bool:
    return (value or "").strip().casefold() not in _PLACEHOLDER_NIK


class IdentityIndex:
    """Employee ID dan NIK yang sudah ada, termasuk baris yang baru diterima di file yang sama."""

    def __init__(self):
        self.ids: dict[str, str] = {}
        self.niks: dict[str, str] = {}

    @classmethod
    def load(cls, tenant) -> IdentityIndex:
        index = cls()
        rows = Employee.objects.filter(tenant=tenant).values_list(
            "employee_id",
            "full_name",
            "nik_lookup",
        )
        for employee_id, full_name, nik_lookup in rows:
            index.ids[(employee_id or "").strip().casefold()] = full_name or ""
            if nik_lookup:
                index.niks[nik_lookup] = full_name or ""
        return index

    def duplicate_reason(self, employee_id: str, full_name: str, nik: str) -> str | None:
        eid = (employee_id or "").strip()
        if eid.casefold() in self.ids:
            return f"Employee ID '{eid}' sudah terdaftar. Data lama tidak diubah."

        raw_nik = (nik or "").strip()
        if not is_real_nik(raw_nik):
            return None

        existing_name = self.niks.get(compute_nik_lookup(raw_nik))
        if existing_name is None:
            return None
        if normalize_person_name(full_name) == normalize_person_name(existing_name):
            return f"NIK dan nama sudah terdaftar ({full_name.strip()})."
        return f"NIK sudah terdaftar atas nama {existing_name}."

    def remember(self, employee_id: str, full_name: str, nik: str) -> None:
        eid = (employee_id or "").strip()
        name = (full_name or "").strip()
        if eid:
            self.ids[eid.casefold()] = name
        raw_nik = (nik or "").strip()
        if is_real_nik(raw_nik):
            self.niks[compute_nik_lookup(raw_nik)] = name
