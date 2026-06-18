"""Pemetaan kolom export Talenta → field model Employee / master data."""

from __future__ import annotations

# Header persis seperti export Employee Database Talenta (sumber kebenaran).
TALENTA_EMPLOYEE_COLUMNS: tuple[str, ...] = (
    "Employee ID",
    "Full Name",
    "Organization",
    "Job Position",
    "Job Level",
    "Join Date",
    "Resign Date",
    "Status Employee",
    "End Date",
    "Sign Date",
    "Email",
    "Birth Date",
    "Age",
    "Birth Place",
    "Citizen ID Address",
    "Residential Address",
    "NPWP",
    "PTKP Status",
    "Employee Tax Status",
    "Tax Config",
    "Bank Name",
    "Bank Account",
    "Bank Account Holder",
    "BPJS Ketenagakerjaan",
    "BPJS Kesehatan",
    "NIK (NPWP 16 Digit)",
    "Mobile Phone",
    "Phone",
    "Branch Name",
    "Parent Branch Name",
    "Religion",
    "Gender",
    "Marital Status",
    "Blood Type",
    "Nationality Code",
    "Currency",
    "Length Of Service",
    "Payment Schedule",
    "Approval Line",
    "Manager",
    "Grade",
    "Class",
    "Profile Picture",
    "Cost Center",
    "Cost Center Category",
    "SBU",
    "NPWP 16 digit (new)",
    "Passport",
    "Passport Expiration Date",
    "Jenis Dok. Referensi Bukti Potong",
    "Nomor Dok. Referensi Bukti Potong",
    "Tanggal Dok. Referensi Bukti Potong",
    "TIN (Taxpayer Identification Number)",
)

# Kolom opsional lama (beberapa file export masih memuat Barcode).
TALENTA_OPTIONAL_COLUMNS: tuple[str, ...] = ("Barcode",)

TALENTA_REQUIRED_IMPORT_COLUMNS: tuple[str, ...] = (
    "Employee ID",
    "Full Name",
    "Organization",
    "Job Position",
    "Join Date",
    "Status Employee",
)

# Master data Talenta — nilai unik per kategori, dibuat otomatis saat import.
TALENTA_MASTER_COLUMN_MAP: dict[str, str] = {
    "Religion": "religion",
    "Blood Type": "blood_type",
    "Nationality Code": "nationality",
    "Currency": "currency",
    "Payment Schedule": "payment_schedule",
    "Approval Line": "approval_line",
    "Grade": "grade",
    "Class": "employee_class",
    "Cost Center": "cost_center",
    "Cost Center Category": "cost_center_category",
    "SBU": "sbu",
    "Employee Tax Status": "employee_tax_status",
    "Tax Config": "tax_config",
}
