from datetime import timedelta

from django.utils import timezone

from apps.attendance.models import AttendanceRecord, DailyTimesheet, OvertimeRequest
from apps.core.models import Notification, User
from apps.employees.models import Employee
from apps.employees.services.onboarding import employee_leave_balances_summary
from apps.leave.models import LeaveRequest
from apps.payroll.models import PayrollRun, Payslip
from apps.shifts.models import ShiftAssignment


def _active_employees(user: User, tenant):
    qs = Employee.objects.filter(tenant=tenant).exclude(
        status__in=[Employee.Status.INACTIVE, Employee.Status.RESIGNED]
    )
    if user.plant_id and not user.is_admin:
        qs = qs.filter(plant=user.plant)
    return qs


def _plant_filter(user: User, qs):
    if user.plant_id and not user.is_admin:
        return qs.filter(plant=user.plant)
    return qs


def _latest_punch_photos(employee_ids: list[int]) -> dict[int, str]:
    if not employee_ids:
        return {}

    photos: dict[int, str] = {}
    records = (
        AttendanceRecord.objects.filter(employee_id__in=employee_ids)
        .exclude(check_in_photo="")
        .order_by("employee_id", "-work_date", "-check_in")
    )
    for record in records:
        if record.employee_id in photos:
            continue
        if record.check_in_photo:
            photos[record.employee_id] = record.check_in_photo.url
    return photos


def build_on_leave_today_items(*, user: User, tenant, today) -> list[dict]:
    """Karyawan aktif yang sedang cuti (semua jenis, approved) pada tanggal `today`."""
    active_ids = list(_active_employees(user, tenant).values_list("id", flat=True))
    if not active_ids:
        return []

    leave_requests = (
        LeaveRequest.objects.filter(
            tenant=tenant,
            status=LeaveRequest.Status.APPROVED,
            start_date__lte=today,
            end_date__gte=today,
            employee_id__in=active_ids,
        )
        .select_related("employee", "employee__department", "leave_type")
        .order_by("employee__full_name", "start_date")
    )

    employee_ids = []
    seen: set[int] = set()
    for request in leave_requests:
        if request.employee_id in seen:
            continue
        seen.add(request.employee_id)
        employee_ids.append(request.employee_id)

    photos = _latest_punch_photos(employee_ids)
    items: list[dict] = []
    seen.clear()
    for request in leave_requests:
        if request.employee_id in seen:
            continue
        seen.add(request.employee_id)
        items.append(
            {
                "employee": request.employee,
                "leave_request": request,
                "photo_url": photos.get(request.employee_id, ""),
            }
        )
    return items


def build_dashboard_context(*, user: User, tenant, today, profile):
    """Aggregate dashboard widgets from existing HRIS data."""
    context = {
        "show_ops": user.is_hr,
        "stats_extra": {
            "present_today": 0,
            "on_leave_today": 0,
            "absent_today": 0,
        },
        "recent_notifications": [],
        "pending_leave_items": [],
        "pending_overtime_items": [],
        "attendance_week": [],
        "attendance_week_max": 1,
        "leave_balances": [],
        "today_shift": None,
        "latest_payroll": None,
        "latest_payslip": None,
        "profile_summary": None,
        "on_leave_today_items": [],
    }

    if not tenant:
        return context

    context["recent_notifications"] = list(
        Notification.objects.filter(user=user).order_by("-created_at")[:5]
    )

    active_emp = _active_employees(user, tenant)
    active_ids = list(active_emp.values_list("id", flat=True))

    on_leave_today_items = build_on_leave_today_items(
        user=user,
        tenant=tenant,
        today=today,
    )
    on_leave_ids = {item["employee"].id for item in on_leave_today_items}
    context["on_leave_today_items"] = on_leave_today_items

    present_qs = _plant_filter(
        user,
        AttendanceRecord.objects.filter(
            tenant=tenant,
            work_date=today,
            check_in__isnull=False,
            employee_id__in=active_ids,
        ),
    )
    present_ids = set(present_qs.values_list("employee_id", flat=True))

    context["stats_extra"] = {
        "present_today": len(present_ids),
        "on_leave_today": len(on_leave_ids),
        "absent_today": max(
            0,
            len(active_ids) - len(present_ids) - len(on_leave_ids),
        ),
    }

    week = []
    week_max = 0
    for offset in range(6, -1, -1):
        work_date = today - timedelta(days=offset)
        count = _plant_filter(
            user,
            DailyTimesheet.objects.filter(
                tenant=tenant,
                work_date=work_date,
                employee_id__in=active_ids,
            ),
        ).count()
        week_max = max(week_max, count)
        week.append({"date": work_date, "count": count})
    context["attendance_week"] = week
    context["attendance_week_max"] = week_max or 1

    if user.is_hr:
        context["pending_leave_items"] = list(
            LeaveRequest.objects.filter(
                tenant=tenant,
                status=LeaveRequest.Status.PENDING,
                employee_id__in=active_ids,
            )
            .select_related("employee", "leave_type")
            .order_by("-created_at")[:5]
        )
        context["pending_overtime_items"] = list(
            OvertimeRequest.objects.filter(
                tenant=tenant,
                status=OvertimeRequest.Status.PENDING,
                employee_id__in=active_ids,
            )
            .select_related("employee", "overtime_type")
            .order_by("-created_at")[:5]
        )
        payroll_qs = PayrollRun.objects.filter(tenant=tenant)
        if user.plant_id and not user.is_admin:
            payroll_qs = payroll_qs.filter(plant=user.plant)
        context["latest_payroll"] = payroll_qs.select_related("plant").order_by(
            "-period_start"
        ).first()

    if profile:
        context["leave_balances"] = employee_leave_balances_summary(profile)
        context["today_shift"] = (
            ShiftAssignment.objects.filter(employee=profile, work_date=today)
            .select_related("shift", "employee", "employee__plant")
            .first()
        )
        context["latest_payslip"] = (
            Payslip.objects.filter(employee=profile)
            .select_related("payroll_run", "payroll_run__plant")
            .order_by("-payroll_run__period_start")
            .first()
        )
        job = profile.job_position
        dept = profile.department
        context["profile_summary"] = {
            "employee_id": profile.employee_id,
            "department": dept.name if dept else "—",
            "position": job.title if job else "—",
            "ptkp": profile.tax_status or "—",
            "plant": profile.plant.name if profile.plant_id else "—",
            "status": profile.get_status_display(),
        }

    return context
