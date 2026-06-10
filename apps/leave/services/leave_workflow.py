from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.attendance.services.timesheet import recalculate_timesheet_range
from apps.core.models import Notification
from apps.core.services.notifications import notify_user
from apps.leave.models import LeaveBalance, LeaveRequest, LeaveType


class LeaveError(Exception):
    pass


def _business_days(start, end, is_half_day=False) -> Decimal:
    if is_half_day:
        return Decimal("0.5")
    days = (end - start).days + 1
    return Decimal(max(days, 0))


def _notify_manager_pending(leave_request):
    manager = leave_request.employee.manager
    if manager and manager.user_id:
        notify_user(
            tenant=leave_request.tenant,
            user=manager.user,
            category=Notification.Category.LEAVE,
            title="Pengajuan cuti baru",
            message=(
                f"{leave_request.employee.full_name} mengajukan cuti "
                f"{leave_request.leave_type.code} ({leave_request.start_date} — {leave_request.end_date})"
            ),
            link=f"{settings.HRIS_SITE_URL}/leave/",
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

    if leave_type.code == "CT" and balance.remaining < days:
        raise LeaveError(f"Saldo cuti tidak cukup. Sisa: {balance.remaining} hari.")

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

    if leave_type.code == "CT":
        balance.pending += days
        balance.remaining -= days
        balance.save(update_fields=["pending", "remaining", "updated_at"])

    _notify_manager_pending(req)
    return req


@transaction.atomic
def approve_leave_request(request: LeaveRequest, approver) -> LeaveRequest:
    if request.status != LeaveRequest.Status.PENDING:
        raise LeaveError("Pengajuan sudah diproses.")

    request.status = LeaveRequest.Status.APPROVED
    request.approver = approver
    request.approved_at = timezone.now()
    request.save(update_fields=["status", "approver", "approved_at", "updated_at"])

    if request.leave_type.code == "CT":
        balance = get_or_create_balance(request.employee, request.leave_type)
        balance.pending -= request.days
        balance.used += request.days
        balance.save(update_fields=["pending", "used", "updated_at"])

    recalculate_timesheet_range(
        request.employee,
        request.start_date,
        request.end_date,
    )
    _notify_employee_status(request, approved=True)
    return request


@transaction.atomic
def reject_leave_request(request: LeaveRequest, approver, reason="") -> LeaveRequest:
    if request.status != LeaveRequest.Status.PENDING:
        raise LeaveError("Pengajuan sudah diproses.")

    request.status = LeaveRequest.Status.REJECTED
    request.approver = approver
    request.approved_at = timezone.now()
    request.rejection_reason = reason
    request.save(
        update_fields=["status", "approver", "approved_at", "rejection_reason", "updated_at"]
    )

    if request.leave_type.code == "CT":
        balance = get_or_create_balance(request.employee, request.leave_type)
        balance.pending -= request.days
        balance.remaining += request.days
        balance.save(update_fields=["pending", "remaining", "updated_at"])

    _notify_employee_status(request, approved=False)
    return request


@transaction.atomic
def cancel_leave_request(request: LeaveRequest, actor) -> LeaveRequest:
    if request.status != LeaveRequest.Status.PENDING:
        raise LeaveError("Hanya pengajuan pending yang bisa dibatalkan.")

    request.status = LeaveRequest.Status.CANCELLED
    request.approver = actor
    request.approved_at = timezone.now()
    request.save(update_fields=["status", "approver", "approved_at", "updated_at"])

    if request.leave_type.code == "CT":
        balance = get_or_create_balance(request.employee, request.leave_type)
        balance.pending -= request.days
        balance.remaining += request.days
        balance.save(update_fields=["pending", "remaining", "updated_at"])

    return request
