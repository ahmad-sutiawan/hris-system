from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.attendance.services.timesheet import recalculate_timesheet_range
from apps.core.models import ApprovalLine
from apps.core.services.approval_chain import (
    can_user_approve_step,
    next_step_order,
    notify_step_approver,
)
from apps.core.models import Notification
from apps.core.services.notifications import notify_user
from apps.core.services.request_notifications import (
    dismiss_leave_request_notifications,
    leave_request_link,
)
from apps.leave.models import LeaveBalance, LeaveRequest, LeaveType


class LeaveError(Exception):
    pass


BALANCE_TRACKED_LEAVE_CODES = frozenset({"CT", "CL"})


def _tracks_leave_balance(leave_type: LeaveType) -> bool:
    return leave_type.code in BALANCE_TRACKED_LEAVE_CODES


def _business_days(start, end, is_half_day=False) -> Decimal:
    if is_half_day:
        return Decimal("0.5")
    days = (end - start).days + 1
    return Decimal(max(days, 0))


def _notify_manager_pending(leave_request):
    notify_step_approver(
        tenant=leave_request.tenant,
        employee=leave_request.employee,
        request_type=ApprovalLine.RequestType.LEAVE,
        step_order=leave_request.approval_step or 1,
        category=Notification.Category.LEAVE,
        title="Pengajuan cuti baru",
        message=(
            f"{leave_request.employee.full_name} mengajukan cuti "
            f"{leave_request.leave_type.code} ({leave_request.start_date} — {leave_request.end_date})"
        ),
        link=leave_request_link(leave_request),
    )


def _notify_employee_status(leave_request, approved=True):
    employee_user = leave_request.employee.user
    if not employee_user:
        return
    if approved:
        title = "Cuti disetujui"
        message = (
            f"Pengajuan cuti {leave_request.leave_type.code} "
            f"({leave_request.start_date} — {leave_request.end_date}) telah disetujui."
        )
    else:
        title = "Cuti ditolak"
        message = (
            f"Pengajuan cuti {leave_request.leave_type.code} ditolak. "
            f"Alasan: {leave_request.rejection_reason or '-'}"
        )
    notify_user(
        tenant=leave_request.tenant,
        user=employee_user,
        category=Notification.Category.LEAVE,
        title=title,
        message=message,
        link=f"{settings.HRIS_SITE_URL}/leave/",
    )


@transaction.atomic
def get_or_create_balance(employee, leave_type, year=None) -> LeaveBalance:
    year = year or timezone.localdate().year
    balance, created = LeaveBalance.objects.get_or_create(
        employee=employee,
        leave_type=leave_type,
        year=year,
        defaults={
            "tenant": employee.tenant,
            "opening_balance": leave_type.default_quota_days,
            "accrued": leave_type.default_quota_days,
            "remaining": leave_type.default_quota_days,
        },
    )
    return balance


@transaction.atomic
def submit_leave_request(
    *,
    employee,
    leave_type,
    start_date,
    end_date,
    reason="",
    is_half_day=False,
) -> LeaveRequest:
    if end_date < start_date:
        raise LeaveError("Tanggal selesai harus >= tanggal mulai.")

    days = _business_days(start_date, end_date, is_half_day)
    balance = get_or_create_balance(employee, leave_type)

    if _tracks_leave_balance(leave_type):
        balance = LeaveBalance.objects.select_for_update().get(pk=balance.pk)
        if balance.remaining < days:
            raise LeaveError(
                f"Saldo cuti {leave_type.code} tidak cukup. Sisa: {balance.remaining} hari."
            )

    req = LeaveRequest.objects.create(
        tenant=employee.tenant,
        employee=employee,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        days=days,
        is_half_day=is_half_day,
        reason=reason,
        status=LeaveRequest.Status.PENDING,
    )

    if _tracks_leave_balance(leave_type):
        balance.pending += days
        balance.remaining -= days
        balance.save(update_fields=["pending", "remaining", "updated_at"])

    _notify_manager_pending(req)
    return req


def _notify_next_approver(leave_request, step_order: int):
    notify_step_approver(
        tenant=leave_request.tenant,
        employee=leave_request.employee,
        request_type=ApprovalLine.RequestType.LEAVE,
        step_order=step_order,
        category=Notification.Category.LEAVE,
        title="Persetujuan cuti (layer berikutnya)",
        message=f"Pengajuan cuti {leave_request.employee.full_name} menunggu persetujuan Anda.",
        link=leave_request_link(leave_request),
    )


@transaction.atomic
def approve_leave_request(leave_request: LeaveRequest, approver) -> LeaveRequest:
    request = LeaveRequest.objects.select_for_update().get(pk=leave_request.pk)
    if request.status != LeaveRequest.Status.PENDING:
        raise LeaveError("Pengajuan sudah diproses.")
    current_step = request.approval_step or 1
    if not can_user_approve_step(
        approver,
        request.employee,
        ApprovalLine.RequestType.LEAVE,
        current_step,
    ):
        raise LeaveError("Anda tidak berwenang menyetujui pengajuan cuti ini.")

    next_step = next_step_order(
        request.tenant,
        ApprovalLine.RequestType.LEAVE,
        current_step,
    )
    if next_step:
        request.approval_step = next_step
        request.save(update_fields=["approval_step", "updated_at"])
        _notify_next_approver(request, next_step)
        return request

    request.status = LeaveRequest.Status.APPROVED
    request.approver = approver
    request.approved_at = timezone.now()
    request.save(update_fields=["status", "approver", "approved_at", "updated_at"])

    if _tracks_leave_balance(request.leave_type):
        year = timezone.localdate().year
        balance = LeaveBalance.objects.select_for_update().get(
            employee=request.employee,
            leave_type=request.leave_type,
            year=year,
        )
        balance.pending -= request.days
        balance.used += request.days
        balance.save(update_fields=["pending", "used", "updated_at"])

    recalculate_timesheet_range(
        request.employee,
        request.start_date,
        request.end_date,
    )
    _notify_employee_status(request, approved=True)
    dismiss_leave_request_notifications(request)
    return request


@transaction.atomic
def reject_leave_request(leave_request: LeaveRequest, approver, reason="") -> LeaveRequest:
    request = LeaveRequest.objects.select_for_update().get(pk=leave_request.pk)
    if request.status != LeaveRequest.Status.PENDING:
        raise LeaveError("Pengajuan sudah diproses.")
    current_step = request.approval_step or 1
    if not can_user_approve_step(
        approver,
        request.employee,
        ApprovalLine.RequestType.LEAVE,
        current_step,
    ):
        raise LeaveError("Anda tidak berwenang menolak pengajuan cuti ini.")

    request.status = LeaveRequest.Status.REJECTED
    request.approver = approver
    request.approved_at = timezone.now()
    request.rejection_reason = reason
    request.save(
        update_fields=["status", "approver", "approved_at", "rejection_reason", "updated_at"]
    )

    if _tracks_leave_balance(request.leave_type):
        year = timezone.localdate().year
        balance = LeaveBalance.objects.select_for_update().get(
            employee=request.employee,
            leave_type=request.leave_type,
            year=year,
        )
        balance.pending -= request.days
        balance.remaining += request.days
        balance.save(update_fields=["pending", "remaining", "updated_at"])

    _notify_employee_status(request, approved=False)
    dismiss_leave_request_notifications(request)
    return request


@transaction.atomic
def cancel_leave_request(leave_request: LeaveRequest, actor) -> LeaveRequest:
    request = LeaveRequest.objects.select_for_update().get(pk=leave_request.pk)
    if request.status != LeaveRequest.Status.PENDING:
        raise LeaveError("Hanya pengajuan pending yang bisa dibatalkan.")

    request.status = LeaveRequest.Status.CANCELLED
    request.approver = actor
    request.approved_at = timezone.now()
    request.save(update_fields=["status", "approver", "approved_at", "updated_at"])

    if _tracks_leave_balance(request.leave_type):
        year = timezone.localdate().year
        balance = LeaveBalance.objects.select_for_update().get(
            employee=request.employee,
            leave_type=request.leave_type,
            year=year,
        )
        balance.pending -= request.days
        balance.remaining += request.days
        balance.save(update_fields=["pending", "remaining", "updated_at"])

    dismiss_leave_request_notifications(request)
    return request
