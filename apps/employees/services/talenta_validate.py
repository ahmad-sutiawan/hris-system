"""Validasi kapasitas field & header file export Talenta (employee_db.xlsx)."""

from __future__ import annotations

from dataclasses import dataclass

from apps.employees.talenta_vocabulary import TALENTA_COLUMNS

# Batas panjang string per kolom Excel → field Employee / master (MySQL).
TALENTA_STRING_LIMITS: dict[str, int] = {
    "Employee ID": 64,
    "Full Name": 200,
    "Barcode": 64,
    "Organization": 200,
    "Job Position": 200,
    "Job Level": 100,
    "Status Employee": 32,
    "Email": 254,
    "Age": 32,
    "Birth Place": 120,
    "NPWP": 512,
    "PTKP Status": 16,
    "Employee Tax Status": 64,
    "Tax Config": 64,
    "Bank Name": 100,
    "Bank Account": 512,
    "Bank Account Holder": 512,
    "BPJS Ketenagakerjaan": 512,
    "BPJS Kesehatan": 512,
    "NIK (NPWP 16 Digit)": 512,
    "Mobile Phone": 32,
    "Phone": 32,
    "Branch Name": 200,
    "Parent Branch Name": 200,
    "Religion": 200,
    "Gender": 16,
    "Marital Status": 16,
    "Blood Type": 200,
    "Nationality Code": 200,
    "Currency": 200,
    "Length Of Service": 64,
    "Payment Schedule": 200,
    "Approval Line": 200,
    "Manager": 200,
    "Grade": 200,
    "Class": 200,
    "Profile Picture": 500,
    "Cost Center": 200,
    "Cost Center Category": 200,
    "SBU": 200,
    "NPWP 16 digit (new)": 512,
    "Passport": 512,
    "Jenis Dok. Referensi Bukti Potong": 120,
    "Nomor Dok. Referensi Bukti Potong": 120,
    "TIN (Taxpayer Identification Number)": 512,
}


@dataclass
class TalentaValidationResult:
    ok: bool
    row_count: int
    errors: list[str]
    warnings: list[str]


def validate_talenta_rows(headers: list[str], rows: list[dict]) -> TalentaValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    missing_headers = [col for col in TALENTA_COLUMNS if col not in headers]
    if missing_headers:
        errors.append(f"Kolom hilang: {', '.join(missing_headers)}")

    extra_headers = [h for h in headers if h and h not in TALENTA_COLUMNS]
    if extra_headers:
        warnings.append(f"Kolom tambahan diabaikan: {', '.join(extra_headers)}")

    seen_ids: dict[str, int] = {}
    for row_num, row in enumerate(rows, start=2):
        employee_id = str(row.get("Employee ID") or "").strip()
        if not employee_id:
            errors.append(f"Baris {row_num}: Employee ID kosong.")
            continue
        if employee_id in seen_ids:
            errors.append(
                f"Baris {row_num}: Employee ID duplikat '{employee_id}' "
                f"(sudah di baris {seen_ids[employee_id]})."
            )
        else:
            seen_ids[employee_id] = row_num

        for column, limit in TALENTA_STRING_LIMITS.items():
            raw = row.get(column)
            if raw is None:
                continue
            text = str(raw).strip()
            if not text:
                continue
            if len(text) > limit:
                errors.append(
                    f"Baris {row_num} kolom '{column}': panjang {len(text)} "
                    f"melebihi batas {limit}."
                )

    return TalentaValidationResult(
        ok=not errors,
        row_count=len(rows),
        errors=errors,
        warnings=warnings,
    )


def validate_talenta_xlsx(file_bytes: bytes) -> TalentaValidationResult:
    from apps.employees.services.import_talenta import _load_rows

    headers, rows = _load_rows(file_bytes)
    return validate_talenta_rows(headers, rows)
