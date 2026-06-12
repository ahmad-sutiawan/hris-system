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
    }

    if not tenant:
        return context

    context["recent_notifications"] = list(
        Notification.objects.filter(user=user).order_by("-created_at")[:5]
    )

    active_emp = _active_employees(user, tenant)
    active_ids = list(active_emp.values_list("id", flat=True))

    on_leave_ids = set(
        LeaveRequest.objects.filter(
            tenant=tenant,
            status=LeaveRequest.Status.APPROVED,
            start_date__lte=today,
            end_date__gte=today,
            employee_id__in=active_ids,
        ).values_list("employee_id", flat=True)
    )

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
            .select_related("shift")
            .first()
        )
        context["latest_payslip"] = (
            Payslip.objects.filter(employee=profile)
            .select_related("payroll_run", "payroll_run__plant")
            .order_by("-payroll_run__period_start")
            .first()
        )
        context["profile_summary"] = {
            "employee_id": profile.employee_id,
            "department": profile.department.name if profile.department_id else "—",
            "position": profile.job_position.name if profile.job_position_id else "—",
            "grade": profile.grade_label or "—",
            "plant": profile.plant.name if profile.plant_id else "—",
            "status": profile.get_status_display(),
        }

    return context
