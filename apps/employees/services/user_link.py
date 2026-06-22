from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.core.models import User
from apps.employees.models import Employee
from apps.employees.querysets import employee_login_qs


def link_user_to_employee(user) -> Employee | None:
    """Match an auth user to an employee record when not yet linked."""
    if not user or not user.tenant_id:
        return None

    profile = getattr(user, "employee_profile", None)
    if profile:
        return profile

    if user.role not in {User.Role.EMPLOYEE, User.Role.MANAGER}:
        return None

    qs = employee_login_qs().filter(tenant=user.tenant).filter(user__isnull=True).exclude(
        status__in=[Employee.Status.INACTIVE, Employee.Status.RESIGNED]
    )
    if user.plant_id:
        qs = qs.filter(plant=user.plant)

    match = None
    if user.email:
        match = qs.filter(email__iexact=user.email).first()
    if not match:
        match = qs.filter(employee_id__iexact=user.username).first()
    if not match:
        match = qs.filter(full_name__icontains=user.username).first()

    if match:
        match.user = user
        match.save(update_fields=["user", "updated_at"])
        return match

    return None


def _auto_provision_enabled() -> bool:
    return getattr(settings, "HRIS_AUTO_PROVISION_EMPLOYEES", settings.DEBUG)


def provision_employee_for_user(user) -> Employee | None:
    """Create a minimal employee record for login-only accounts (dev/demo)."""
    if not user or not user.tenant_id or not user.plant_id:
        return None
    if user.role not in {User.Role.EMPLOYEE, User.Role.MANAGER}:
        return None
    if getattr(user, "employee_profile", None):
        return user.employee_profile

    base_id = f"{user.plant.code}-{user.username.upper()}"
    employee_id = base_id
    suffix = 1
    while Employee.objects.filter(tenant=user.tenant, employee_id=employee_id).exists():
        suffix += 1
        employee_id = f"{base_id}-{suffix}"

    display_name = user.get_full_name().strip() or user.username.replace("_", " ").title()
    employee = Employee.objects.create(
        tenant=user.tenant,
        plant=user.plant,
        employee_id=employee_id,
        full_name=display_name,
        email=user.email or "",
        join_date=timezone.localdate(),
        status=Employee.Status.PERMANENT,
        user=user,
    )
    return employee


def ensure_employee_profile(user) -> Employee | None:
    """Link an existing employee row or optionally auto-provision in dev."""
    linked = link_user_to_employee(user)
    if linked:
        return linked
    if _auto_provision_enabled():
        return provision_employee_for_user(user)
    return None


def available_users_for_employee(tenant, current_user_id=None):
    qs = User.objects.filter(tenant=tenant, is_active=True).filter(
        Q(employee_profile__isnull=True) | Q(pk=current_user_id)
    )
    return qs.order_by("username")
