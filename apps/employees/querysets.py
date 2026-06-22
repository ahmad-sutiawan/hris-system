"""Queryset helpers — hindari dekripsi field sensitif saat tidak diperlukan."""

from apps.employees.models import Employee

# Field terenkripsi — defer saat lookup login agar tidak gagal jika key sementara salah.
ENCRYPTED_EMPLOYEE_FIELDS = (
    "nik",
    "npwp_16_digit",
    "base_salary",
    "allowance_transport",
    "allowance_meal",
    "allowance_position",
    "bank_account_number",
    "bank_account_name",
    "npwp",
    "bpjs_kesehatan_number",
    "bpjs_ketenagakerjaan_number",
    "passport_number",
    "tin",
)


def employee_login_qs():
    """Karyawan untuk autentikasi: tanpa memuat kolom terenkripsi."""
    return Employee.objects.defer(*ENCRYPTED_EMPLOYEE_FIELDS).select_related(
        "user", "tenant", "plant"
    )
