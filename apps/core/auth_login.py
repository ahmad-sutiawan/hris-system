"""Login karyawan via NIK atau Employee ID; admin/HR tetap pakai username."""

from __future__ import annotations

import logging

from django.contrib.auth import get_user_model

from apps.employees.models import Employee
from apps.employees.nik_lookup import compute_nik_lookup
from apps.employees.querysets import employee_login_qs

User = get_user_model()
logger = logging.getLogger(__name__)

# Role yang login via username (bukan NIK/employee_id).
_USERNAME_LOGIN_ROLES = {
    User.Role.ADMIN,
    User.Role.HR,
    User.Role.FINANCE,
    User.Role.AUDITOR,
}


def normalize_login_identifier(value: str) -> str:
    return (value or "").strip()


def _best_employee_match(qs) -> Employee | None:
    """Pilih karyawan dengan akun aktif jika ada duplikat lintas tenant."""
    employees = list(qs)
    if not employees:
        return None
    for emp in employees:
        if emp.user_id and emp.user.is_active:
            return emp
    return employees[0]


def find_employee_by_login_identifier(identifier: str, *, employee_id_hint: str | None = None) -> Employee | None:
    """Cari karyawan dari NIK atau nomor Employee ID."""
    ident = normalize_login_identifier(identifier)
    id_hint = normalize_login_identifier(employee_id_hint or "")
    if not ident and not id_hint:
        return None

    if ident and not id_hint:
        emp = _best_employee_match(employee_login_qs().filter(employee_id__iexact=ident))
        if emp:
            return emp
        lookup = compute_nik_lookup(ident)
        if lookup:
            return _best_employee_match(employee_login_qs().filter(nik_lookup=lookup))
        return None

    if id_hint:
        qs = employee_login_qs().filter(employee_id__iexact=id_hint)
        if ident and ident.lower() != id_hint.lower():
            lookup = compute_nik_lookup(ident)
            if lookup:
                qs = qs.filter(nik_lookup=lookup)
        emp = _best_employee_match(qs)
        if emp:
            return emp

    if ident:
        lookup = compute_nik_lookup(ident)
        if lookup:
            return _best_employee_match(employee_login_qs().filter(nik_lookup=lookup))

    return None


def resolve_user_for_login(identifier: str, *, employee_id_hint: str | None = None) -> User | None:
    """
    Map input login ke User:
    - Karyawan/manager: NIK atau employee_id (hint ID dari password jika ada)
    - Admin/HR/finance/auditor: username akun (mis. admin)
    """
    ident = normalize_login_identifier(identifier)
    if not ident and not normalize_login_identifier(employee_id_hint or ""):
        return None

    employee = find_employee_by_login_identifier(ident, employee_id_hint=employee_id_hint)
    if employee and employee.user_id:
        user = employee.user
        if user.is_active:
            return user

    user = User.objects.filter(username__iexact=ident, is_active=True).first()
    if not user:
        return None

    if user.is_superuser or user.is_admin:
        return user

    if user.role in _USERNAME_LOGIN_ROLES:
        return user

    # Karyawan/manager hanya lewat NIK atau Employee ID — bukan username lama (mis. budi).
    return None


def employee_login_password(employee: Employee) -> str:
    """Password karyawan = Employee ID (teks asli, mis. 525)."""
    return (employee.employee_id or "").strip()


def apply_employee_credentials(employee: Employee, *, role: str | None = None) -> User | None:
    """
    Sinkronkan akun login karyawan:
    - username = employee_id
    - password = employee_id
    Login bisa pakai NIK atau employee_id di field username.
    """
    if not employee.employee_id:
        return None

    user = employee.user
    if user and (user.is_superuser or user.role == User.Role.ADMIN):
        return user

    desired_username = employee.employee_id
    password = employee_login_password(employee)

    if not user:
        existing = User.objects.filter(username__iexact=desired_username).first()
        if existing:
            linked = getattr(existing, "employee_profile", None)
            if linked and linked.pk != employee.pk:
                desired_username = f"{employee.employee_id}@{employee.tenant.slug}"
                existing = User.objects.filter(username__iexact=desired_username).first()
            elif linked is None and existing.tenant_id != employee.tenant_id:
                desired_username = f"{employee.employee_id}@{employee.tenant.slug}"
                existing = User.objects.filter(username__iexact=desired_username).first()

        if existing:
            linked = getattr(existing, "employee_profile", None)
            if linked and linked.pk not in (None, employee.pk):
                return None
            user = existing
            employee.user = user
            employee.save(update_fields=["user", "updated_at"])

        if not user:
            if User.objects.filter(username__iexact=desired_username).exists():
                return None
            user = User(
                username=desired_username,
                tenant=employee.tenant,
                plant=employee.plant,
                role=role or User.Role.EMPLOYEE,
                is_active=True,
            )
            user.set_password(password)
            user.save()
            employee.user = user
            employee.save(update_fields=["user", "updated_at"])
            return user

    password_fields_changed = False
    if not User.objects.filter(username__iexact=desired_username).exclude(pk=user.pk).exists():
        if user.username != desired_username:
            user.username = desired_username
            password_fields_changed = True

    if not user.check_password(password):
        user.set_password(password)
        password_fields_changed = True

    user.tenant = employee.tenant
    user.plant = employee.plant
    if role:
        user.role = role
    elif user.role not in {User.Role.EMPLOYEE, User.Role.MANAGER}:
        user.role = User.Role.EMPLOYEE
    user.is_active = True

    update_fields = ["tenant", "plant", "role", "is_active", "username"]
    if password_fields_changed:
        update_fields.append("password")
    user.save(update_fields=update_fields)
    return user
