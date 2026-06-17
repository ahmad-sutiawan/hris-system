from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.attendance.models import OvertimeRequest
from apps.attendance.services.overtime_compensation import credit_overtime_as_leave
from apps.attendance.services.policy import ot_before_overtime_enabled
from apps.attendance.services.timesheet import recalculate_daily_timesheet
from apps.core.models import ApprovalLine, Notification
from apps.core.services.approval_chain import (
    can_user_approve_step,
    next_step_order,
    notify_step_approver,
)
from apps.core.services.notifications import notify_user
from apps.core.services.request_notifications import (
    dismiss_overtime_request_notifications,
    overtime_request_link,
)


class OvertimeError(Exception):
    pass


def get_raw_overtime_minutes(employee, work_date) -> tuple[int, int]:
    """Return uncapped OT minutes from current punches vs shift schedule."""
    from apps.attendance.services.timesheet_engine import calculate_timesheet_metrics
    from apps.attendance.models import AttendanceRecord
    from apps.attendance.services.policy import ot_before_overtime_enabled
    from apps.shifts.models import ShiftAssignment

    assignment = ShiftAssignment.objects.filter(
        employee=employee,
        work_date=work_date,
    ).select_related("shift").first()
    record = AttendanceRecord.objects.filter(employee=employee, work_date=work_date).first()
    if not assignment or not record or not record.check_in or not record.check_out:
        return 0, 0

    shift = assignment.shift
    ot_before_enabled = ot_before_overtime_enabled(employee.tenant, employee.plant)
    metrics = calculate_timesheet_metrics(
        work_date=work_date,
        scheduled_check_in=assignment.scheduled_check_in,
        scheduled_check_out=assignment.scheduled_check_out,
        check_in=record.check_in,
        check_out=record.check_out,
        break_minutes=shift.break_minutes if shift else 0,
        grace_period_minutes=shift.grace_period_minutes if shift else 15,
        schedule_working_hours=None,
        ot_before_enabled=ot_before_enabled,
    )
    return metrics["ot_before_minutes"], metrics["ot_after_minutes"]


def _notify_manager_pending(overtime_request: OvertimeRequest):
    notify_step_approver(
        tenant=overtime_request.tenant,
        employee=overtime_request.employee,
        request_type=ApprovalLine.RequestType.OVERTIME,
        step_order=overtime_request.approval_step or 1,
        category=Notification.Category.ATTENDANCE,
        title="Pengajuan lembur baru",
        message=(
            f"{overtime_request.employee.full_name} mengajukan lembur "
            f"{overtime_request.work_date} "
            f"({overtime_request.overtime_type.name if overtime_request.overtime_type else '—'}) "
            f"(sebelum: {overtime_request.ot_before_minutes} m, "
            f"sesudah: {overtime_request.ot_after_minutes} m)"
        ),
        link=overtime_request_link(overtime_request),
    )


def _notify_employee_status(overtime_request: OvertimeRequest, *, approved=True):
    employee_user = overtime_request.employee.user
    if not employee_user:
        return
    if approved:
        title = "Lembur disetujui"
        comp_label = (
            "ditambahkan ke jatah cuti"
            if overtime_request.compensation_mode == OvertimeRequest.CompensationMode.LEAVE
            else "akan diuangkan di payroll"
        )
        message = (
            f"Pengajuan lembur {overtime_request.work_date} telah disetujui "
            f"(sebelum: {overtime_request.ot_before_minutes} m, "
            f"sesudah: {overtime_request.ot_after_minutes} m) — kompensasi {comp_label}."
        )
    else:
        title = "Lembur ditolak"
        message = (
            f"Pengajuan lembur {overtime_request.work_date} ditolak. "
            f"Alasan: {overtime_request.rejection_reason or '-'}"
        )
    notify_user(
        tenant=overtime_request.tenant,
        user=employee_user,
        category=Notification.Category.ATTENDANCE,
        title=title,
        message=message,
        link=f"{settings.HRIS_SITE_URL}/overtime/",
    )


@transaction.atomic
def submit_overtime_request(
    *,
    employee,
    work_date,
    overtime_type=None,
    ot_before_minutes=0,
    ot_after_minutes=0,
    compensation_mode=OvertimeRequest.CompensationMode.CASH,
    reason="",
) -> OvertimeRequest:
    if not overtime_type:
        raise OvertimeError("Pilih jenis lembur.")
    if not ot_before_overtime_enabled(employee.tenant, employee.plant):
        ot_before_minutes = 0
    if ot_after_minutes <= 0:
        raise OvertimeError("Isi durasi lembur sesudah shift (minimal 1 menit).")

    pending_exists = OvertimeRequest.objects.filter(
        employee=employee,
        work_date=work_date,
        status=OvertimeRequest.Status.PENDING,
    ).exists()
    if pending_exists:
        raise OvertimeError("Sudah ada pengajuan lembur pending untuk tanggal ini.")

    req = OvertimeRequest.objects.create(
        tenant=employee.tenant,
        employee=employee,
        overtime_type=overtime_type,
        work_date=work_date,
        ot_before_minutes=ot_before_minutes,
        ot_after_minutes=ot_after_minutes,
        compensation_mode=compensation_mode,
        reason=reason,
        status=OvertimeRequest.Status.PENDING,
    )
    _notify_manager_pending(req)
    return req


@transaction.atomic
def approve_overtime_request(overtime_request: OvertimeRequest, approver) -> OvertimeRequest:
    request = OvertimeRequest.objects.select_for_update().get(pk=overtime_request.pk)
    if request.status != OvertimeRequest.Status.PENDING:
        raise OvertimeError("Pengajuan sudah diproses.")
    current_step = request.approval_step or 1
    if not can_user_approve_step(
        approver,
        request.employee,
        ApprovalLine.RequestType.OVERTIME,
        current_step,
    ):
        raise OvertimeError("Anda tidak berwenang menyetujui pengajuan lembur ini.")

    next_step = next_step_order(
        request.tenant,
        ApprovalLine.RequestType.OVERTIME,
        current_step,
    )
    if next_step:
        request.approval_step = next_step
        request.save(update_fields=["approval_step", "updated_at"])
        notify_step_approver(
            tenant=request.tenant,
            employee=request.employee,
            request_type=ApprovalLine.RequestType.OVERTIME,
            step_order=next_step,
            category=Notification.Category.OVERTIME,
            title="Persetujuan lembur (layer berikutnya)",
            message=f"Pengajuan lembur {request.employee.full_name} menunggu persetujuan Anda.",
            link=overtime_request_link(request),
        )
        return request

    if OvertimeRequest.objects.filter(
        employee=request.employee,
        work_date=request.work_date,
        status=OvertimeRequest.Status.APPROVED,
    ).exclude(pk=request.pk).exists():
        raise OvertimeError("Sudah ada lembur disetujui untuk tanggal ini.")

    raw_before, raw_after = get_raw_overtime_minutes(request.employee, request.work_date)
    if not ot_before_overtime_enabled(request.tenant, request.employee.plant):
        raw_before = 0
    request.ot_before_minutes = min(request.ot_before_minutes, raw_before)
    request.ot_after_minutes = min(request.ot_after_minutes, raw_after)
    request.status = OvertimeRequest.Status.APPROVED
    request.approver = approver
    request.approved_at = timezone.now()
    request.save(
        update_fields=[
            "status",
            "ot_before_minutes",
            "ot_after_minutes",
            "approver",
            "approved_at",
            "updated_at",
        ]
    )

    recalculate_daily_timesheet(request.employee, request.work_date)

    if request.compensation_mode == OvertimeRequest.CompensationMode.LEAVE:
        credit_overtime_as_leave(request)

    _notify_employee_status(request, approved=True)
    dismiss_overtime_request_notifications(request)
    return request


@transaction.atomic
def reject_overtime_request(overtime_request: OvertimeRequest, approver, reason="") -> OvertimeRequest:
    request = OvertimeRequest.objects.select_for_update().get(pk=overtime_request.pk)
    if request.status != OvertimeRequest.Status.PENDING:
        raise OvertimeError("Pengajuan sudah diproses.")
    current_step = request.approval_step or 1
    if not can_user_approve_step(
        approver,
        request.employee,
        ApprovalLine.RequestType.OVERTIME,
        current_step,
    ):
        raise OvertimeError("Anda tidak berwenang menolak pengajuan lembur ini.")

    request.status = OvertimeRequest.Status.REJECTED
    request.approver = approver
    request.approved_at = timezone.now()
    request.rejection_reason = reason
    request.save(
        update_fields=["status", "approver", "approved_at", "rejection_reason", "updated_at"]
    )
    _notify_employee_status(request, approved=False)
    dismiss_overtime_request_notifications(request)
    return request


@transaction.atomic
def cancel_overtime_request(overtime_request: OvertimeRequest, actor) -> OvertimeRequest:
    request = OvertimeRequest.objects.select_for_update().get(pk=overtime_request.pk)
    if request.status != OvertimeRequest.Status.PENDING:
        raise OvertimeError("Hanya pengajuan pending yang bisa dibatalkan.")

    request.status = OvertimeRequest.Status.CANCELLED
    request.approver = actor
    request.approved_at = timezone.now()
    request.save(update_fields=["status", "approver", "approved_at", "updated_at"])
    dismiss_overtime_request_notifications(request)
    return request
