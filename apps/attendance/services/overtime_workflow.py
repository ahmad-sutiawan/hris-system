from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.attendance.models import OvertimeRequest
from apps.attendance.services.timesheet import recalculate_daily_timesheet
from apps.core.models import Notification
from apps.core.services.notifications import notify_user


class OvertimeError(Exception):
    pass


def get_raw_overtime_minutes(employee, work_date) -> tuple[int, int]:
    """Return uncapped OT minutes from current punches vs shift schedule."""
    from apps.attendance.services.timesheet_engine import calculate_timesheet_metrics
    from apps.attendance.models import AttendanceRecord
    from apps.core.models import FeatureFlag
    from apps.shifts.models import ShiftAssignment

    assignment = ShiftAssignment.objects.filter(
        employee=employee,
        work_date=work_date,
    ).select_related("shift").first()
    record = AttendanceRecord.objects.filter(employee=employee, work_date=work_date).first()
    if not assignment or not record or not record.check_in or not record.check_out:
        return 0, 0

    shift = assignment.shift
    ot_before_enabled = FeatureFlag.objects.filter(
        tenant=employee.tenant,
        plant=employee.plant,
        key="ot_before_split",
        enabled=True,
    ).exists()
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
    manager = overtime_request.employee.manager
    if manager and manager.user_id:
        notify_user(
            tenant=overtime_request.tenant,
            user=manager.user,
            category=Notification.Category.ATTENDANCE,
            title="Pengajuan lembur baru",
            message=(
                f"{overtime_request.employee.full_name} mengajukan lembur "
                f"{overtime_request.work_date} "
                f"({overtime_request.overtime_type.name if overtime_request.overtime_type else '—'}) "
                f"(sebelum: {overtime_request.ot_before_minutes} m, "
                f"sesudah: {overtime_request.ot_after_minutes} m)"
            ),
            link=f"{settings.HRIS_SITE_URL}/overtime/",
        )


def _notify_employee_status(overtime_request: OvertimeRequest, *, approved=True):
    employee_user = overtime_request.employee.user
    if not employee_user:
        return
    if approved:
        title = "Lembur disetujui"
        message = (
            f"Pengajuan lembur {overtime_request.work_date} telah disetujui "
            f"(sebelum: {overtime_request.ot_before_minutes} m, "
            f"sesudah: {overtime_request.ot_after_minutes} m)."
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
    reason="",
) -> OvertimeRequest:
    if not overtime_type:
        raise OvertimeError("Pilih jenis lembur.")
    if ot_before_minutes <= 0 and ot_after_minutes <= 0:
        raise OvertimeError("Isi durasi lembur sebelum atau sesudah shift (minimal satu > 0).")

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
        reason=reason,
        status=OvertimeRequest.Status.PENDING,
    )
    _notify_manager_pending(req)
    return req


@transaction.atomic
def approve_overtime_request(request: OvertimeRequest, approver) -> OvertimeRequest:
    if request.status != OvertimeRequest.Status.PENDING:
        raise OvertimeError("Pengajuan sudah diproses.")

    raw_before, raw_after = get_raw_overtime_minutes(request.employee, request.work_date)
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
    _notify_employee_status(request, approved=True)
    return request


@transaction.atomic
def reject_overtime_request(request: OvertimeRequest, approver, reason="") -> OvertimeRequest:
    if request.status != OvertimeRequest.Status.PENDING:
        raise OvertimeError("Pengajuan sudah diproses.")

    request.status = OvertimeRequest.Status.REJECTED
    request.approver = approver
    request.approved_at = timezone.now()
    request.rejection_reason = reason
    request.save(
        update_fields=["status", "approver", "approved_at", "rejection_reason", "updated_at"]
    )
    _notify_employee_status(request, approved=False)
    return request


@transaction.atomic
def cancel_overtime_request(request: OvertimeRequest, actor) -> OvertimeRequest:
    if request.status != OvertimeRequest.Status.PENDING:
        raise OvertimeError("Hanya pengajuan pending yang bisa dibatalkan.")

    request.status = OvertimeRequest.Status.CANCELLED
    request.approver = actor
    request.approved_at = timezone.now()
    request.save(update_fields=["status", "approver", "approved_at", "updated_at"])
    return request
