from apps.core.models import User


def can_approve_employee(approver, employee) -> bool:
    """HR/Admin may approve any employee in tenant; manager only direct reports."""
    if not approver.is_authenticated or employee is None:
        return False
    if approver.tenant_id != employee.tenant_id:
        return False
    if approver.is_hr or approver.is_admin:
        return True
    if approver.role == User.Role.MANAGER:
        profile = getattr(approver, "employee_profile", None)
        return bool(profile and employee.manager_id == profile.pk)
    return False
