"""Multi-layer approval resolution."""

from __future__ import annotations

from apps.core.approval import can_approve_employee
from apps.core.models import ApprovalLine, User
from apps.employees.models import Employee


def approval_steps(tenant, request_type: str) -> list[ApprovalLine]:
    return list(
        ApprovalLine.objects.filter(
            tenant=tenant,
            request_type=request_type,
            is_active=True,
        ).order_by("step_order")
    )


def approver_for_step(step: ApprovalLine, employee: Employee) -> User | None:
    if step.approver_kind == ApprovalLine.ApproverKind.DIRECT_MANAGER:
        if employee.manager_id and employee.manager.user_id:
            return employee.manager.user
        return None
    if step.approver_kind == ApprovalLine.ApproverKind.HR_PLANT:
        return (
            User.objects.filter(
                tenant=employee.tenant,
                plant=employee.plant,
                role__in=[User.Role.HR, User.Role.ADMIN],
                is_active=True,
            )
            .order_by("id")
            .first()
        )
    if step.approver_kind == ApprovalLine.ApproverKind.HR_TENANT:
        return (
            User.objects.filter(
                tenant=employee.tenant,
                role__in=[User.Role.HR, User.Role.ADMIN],
                is_active=True,
            )
            .order_by("id")
            .first()
        )
    return None


def can_user_approve_step(user, employee: Employee, request_type: str, current_step: int) -> bool:
    steps = approval_steps(employee.tenant, request_type)
    if not steps:
        return can_approve_employee(user, employee)
    for step in steps:
        if step.step_order < current_step:
            continue
        if step.step_order > current_step:
            return False
        approver = approver_for_step(step, employee)
        return bool(approver and approver.pk == user.pk)
    return can_approve_employee(user, employee)


def next_step_order(tenant, request_type: str, current_step: int) -> int | None:
    steps = approval_steps(tenant, request_type)
    for step in steps:
        if step.step_order > current_step:
            return step.step_order
    return None


def notify_step_approver(
    *,
    tenant,
    employee: Employee,
    request_type: str,
    step_order: int,
    category,
    title: str,
    message: str,
    link: str,
) -> None:
    """Notify the approver configured for a given approval step."""
    from apps.core.services.notifications import notify_user

    steps = approval_steps(tenant, request_type)
    if not steps:
        manager = employee.manager
        user = manager.user if manager and manager.user_id else None
        if user:
            notify_user(
                tenant=tenant,
                user=user,
                category=category,
                title=title,
                message=message,
                link=link,
            )
        return

    step = next((row for row in steps if row.step_order == step_order), None)
    if not step:
        return
    user = approver_for_step(step, employee)
    if user:
        notify_user(
            tenant=tenant,
            user=user,
            category=category,
            title=title,
            message=message,
            link=link,
        )
