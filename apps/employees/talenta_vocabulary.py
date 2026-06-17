"""Label dan kolom UI mengikuti export Excel Talenta (sumber kebenaran)."""

from __future__ import annotations

from django.utils.text import slugify

# Header persis seperti file Excel di folder media
TALENTA_COLUMNS = [
    "Employee ID",
    "Full Name",
    "Barcode",
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
]

# Kolom utama di halaman daftar karyawan (urutan mengikuti Excel)
EMPLOYEE_LIST_COLUMNS = [
    "Employee ID",
    "Full Name",
    "Organization",
    "Job Position",
    "Job Level",
    "Branch Name",
    "Status Employee",
    "Join Date",
    "End Date",
    "Email",
    "Mobile Phone",
    "Gender",
    "Marital Status",
    "PTKP Status",
    "Manager",
]

# Master data terkait karyawan
MASTER_ORGANIZATION = "Organization"
MASTER_JOB_POSITION = "Job Position"
MASTER_JOB_LEVEL = "Job Level"
MASTER_BRANCH = "Branch Name"

# Excel Branch Name → kode plant stabil (3 cabang)
TALENTA_BRANCH_SPECS = (
    ("harian", "BPS_HARIAN"),
    ("spv", "SPV_UP"),
    ("staff", "BPS_STAFF"),
)

STATUS_EMPLOYEE_VALUES = ("Harian", "Contract", "Permanent")

GENDER_EXCEL = {
    "male": "Male",
    "female": "Female",
    "na": "",
}

MARITAL_EXCEL = {
    "single": "Single",
    "married": "Married",
    "divorced": "Divorced",
    "widowed": "Widow",
    "na": "",
}

TALENTA_JOB_LEVEL_RANK = {
    "helper": 1,
    "operator": 2,
    "driver": 2,
    "counter": 2,
    "sortir reject": 2,
    "administration": 3,
    "technician": 3,
    "electrician": 3,
    "sr electrician": 4,
    "inspector": 4,
    "wakil leader": 5,
    "leader": 6,
    "staff": 7,
    "sr staff": 8,
    "supervisor": 9,
    "sr supervisor": 10,
    "asst manager": 11,
    "manager": 12,
    "departement head": 13,
    "chief": 14,
    "direktur": 15,
    "direktur utama": 16,
    "management traine": 4,
}


def gender_to_excel(value: str) -> str:
    if not value:
        return ""
    return GENDER_EXCEL.get(str(value).lower(), "")


def marital_to_excel(value: str) -> str:
    if not value:
        return ""
    return MARITAL_EXCEL.get(str(value).lower(), "")


def parent_branch_name(branch_name: str) -> str:
    """Parent Branch Name di Excel — cabang induk tanpa suffix tipe."""
    if not branch_name:
        return ""
    name = branch_name.strip()
    for suffix in (" (Harian)", " (SPV Up)", " (Staff)"):
        if name.endswith(suffix):
            return name[: -len(suffix)].strip()
    return name


def _normalize_branch_key(name: str) -> str:
    return " ".join((name or "").split()).lower()


def branch_kind_from_excel_name(branch_name: str) -> str:
    """Tentukan jenis cabang dari kolom Branch Name Excel."""
    key = _normalize_branch_key(branch_name)
    if "harian" in key:
        return "harian"
    if "spv" in key:
        return "spv"
    if "staff" in key:
        return "staff"
    # Tanpa suffix di Excel = karyawan Staff (PT Baja Perkasa Sentosa)
    if "baja perkasa sentosa" in key:
        return "staff"
    return "other"


def branch_plant_code(branch_name: str) -> str:
    kind = branch_kind_from_excel_name(branch_name)
    for hint, code in TALENTA_BRANCH_SPECS:
        if hint == kind:
            return code
    base = slugify(branch_name or "plant").upper().replace("-", "_")[:20]
    return base or "PLANT"


def branch_type_from_excel_name(branch_name: str) -> str:
    from apps.core.models import Plant

    kind = branch_kind_from_excel_name(branch_name)
    mapping = {
        "harian": Plant.BranchType.BPS_HARIAN,
        "spv": Plant.BranchType.SPV_UP,
        "staff": Plant.BranchType.BPS_STAFF,
    }
    return mapping.get(kind, Plant.BranchType.OTHER)


def canonical_branch_name(branch_name: str) -> str:
    """Nama Branch Name persis seperti Excel (sumber kebenaran)."""
    return " ".join((branch_name or "").split()) or "Plant Utama"
