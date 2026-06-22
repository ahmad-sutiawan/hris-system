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


def can_approve_request(
    approver,
    employee,
    request_type: str,
    approval_step: int = 1,
    *,
    steps=None,
) -> bool:
    """Respect multi-layer approval lines when configured; else legacy rules."""
    from apps.core.services.approval_chain import approval_steps, can_user_approve_step

    if not employee or not approver.is_authenticated:
        return False
    cached_steps = steps if steps is not None else approval_steps(employee.tenant, request_type)
    if not cached_steps:
        return can_approve_employee(approver, employee)
    return can_user_approve_step(
        approver, employee, request_type, approval_step or 1, steps=cached_steps
    )
