from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.attendance.models import AttendanceRecord
from apps.attendance.serializers import AttendanceRecordSerializer
from apps.attendance.services.punch_ui import get_punch_ui_state
from apps.core.models import Notification
from apps.core.services.announcements import active_announcement_count
from apps.employees.services.user_link import ensure_employee_profile
from apps.employees.services.profile import build_employee_profile_context
from apps.web.services.dashboard import build_dashboard_context


class MobileDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.utils import timezone

        user = request.user
        today = timezone.localdate()
        profile = getattr(user, "employee_profile", None)
        if not profile and user.role in {"employee", "manager"}:
            profile = ensure_employee_profile(user)

        today_record = None
        punch_ui = {
            "status": "pending",
            "can_clock_in": False,
            "can_clock_out": False,
        }
        if profile:
            today_record = AttendanceRecord.objects.filter(
                employee=profile,
                work_date=today,
            ).first()
            punch_ui = get_punch_ui_state(today_record)

        dashboard = build_dashboard_context(
            user=user,
            tenant=user.tenant,
            today=today,
            profile=profile,
        )

        unread_notifications = Notification.objects.filter(
            user=user,
            is_read=False,
        ).count()

        payload = {
            "today": today.isoformat(),
            "punch_ui": punch_ui,
            "today_record": (
                AttendanceRecordSerializer(today_record).data if today_record else None
            ),
            "profile_summary": dashboard.get("profile_summary"),
            "leave_balances": _serialize_leave_balances(dashboard.get("leave_balances") or []),
            "today_shift": _serialize_shift(dashboard.get("today_shift")),
            "latest_payslip": _serialize_payslip(dashboard.get("latest_payslip")),
            "recent_notifications": [
                {
                    "id": n.id,
                    "category": n.category,
                    "title": n.title,
                    "message": n.message,
                    "is_read": n.is_read,
                    "created_at": n.created_at.isoformat(),
                }
                for n in dashboard.get("recent_notifications") or []
            ],
            "unread_notifications": unread_notifications,
            "active_announcements": active_announcement_count(user),
        }
        return Response(payload)


class MobileProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            return Response({"detail": "No employee profile linked."}, status=400)

        ctx = build_employee_profile_context(profile)
        employee = ctx["employee"]
        return Response(
            {
                "employee": {
                    "id": employee.id,
                    "employee_id": employee.employee_id,
                    "full_name": employee.full_name,
                    "email": employee.email,
                    "phone": employee.phone,
                    "status": employee.status,
                    "status_label": employee.get_status_display(),
                    "join_date": employee.join_date.isoformat() if employee.join_date else None,
                    "plant": employee.plant.name if employee.plant_id else None,
                    "plant_code": employee.plant.code if employee.plant_id else None,
                    "department": employee.department.name if employee.department_id else None,
                    "job_title": employee.job_position.title if employee.job_position_id else None,
                    "grade": employee.grade_label or None,
                    "manager_name": employee.manager.full_name if employee.manager_id else None,
                    "salary_scheme": employee.salary_scheme,
                },
                "today": ctx["today"].isoformat(),
                "month_stats": ctx["month_stats"],
                "leave_balances": _serialize_leave_balances(ctx.get("leave_balances") or []),
                "today_assignment": _serialize_shift(ctx.get("today_assignment")),
                "upcoming_shifts": [
                    _serialize_shift(item) for item in ctx.get("upcoming_shifts") or []
                ],
                "today_timesheet": _serialize_timesheet(ctx.get("today_timesheet")),
                "recent_timesheets": [
                    _serialize_timesheet(item) for item in ctx.get("recent_timesheets") or []
                ],
                "latest_payslip": _serialize_payslip(ctx.get("latest_payslip")),
                "total_compensation": str(ctx["total_compensation"]),
                "effective_daily_wage": str(ctx["effective_daily_wage"]),
                "effective_hourly_wage": str(ctx["effective_hourly_wage"]),
            }
        )


def _serialize_leave_balances(balances) -> list[dict]:
    rows = []
    for balance in balances:
        leave_type = getattr(balance, "leave_type", None)
        rows.append(
            {
                "leave_type_code": leave_type.code if leave_type else None,
                "leave_type_name": leave_type.name if leave_type else None,
                "year": balance.year,
                "opening_balance": str(balance.opening_balance),
                "accrued": str(balance.accrued),
                "used": str(balance.used),
                "pending": str(balance.pending),
                "remaining": str(balance.remaining),
            }
        )
    return rows


def _serialize_shift(assignment):
    if not assignment:
        return None
    shift = assignment.shift
    return {
        "work_date": assignment.work_date.isoformat(),
        "shift_code": shift.code if shift else None,
        "shift_name": shift.name if shift else None,
        "scheduled_check_in": (
            assignment.scheduled_check_in.isoformat()
            if assignment.scheduled_check_in
            else None
        ),
        "scheduled_check_out": (
            assignment.scheduled_check_out.isoformat()
            if assignment.scheduled_check_out
            else None
        ),
    }


def _serialize_timesheet(ts):
    if not ts:
        return None
    return {
        "work_date": ts.work_date.isoformat(),
        "shift_code": ts.shift_code,
        "check_in": ts.check_in.isoformat() if ts.check_in else None,
        "check_out": ts.check_out.isoformat() if ts.check_out else None,
        "late_in_minutes": ts.late_in_minutes,
        "early_out_minutes": ts.early_out_minutes,
        "paid_working_hours": str(ts.paid_working_hours),
        "ot_before_minutes": ts.ot_before_minutes,
        "ot_after_minutes": ts.ot_after_minutes,
        "attendance_code": ts.attendance_code.code if ts.attendance_code_id else None,
    }


def _serialize_payslip(payslip):
    if not payslip:
        return None
    run = payslip.payroll_run
    return {
        "id": payslip.id,
        "period_start": run.period_start.isoformat(),
        "period_end": run.period_end.isoformat(),
        "net_amount": str(payslip.net_amount),
        "gross_amount": str(payslip.gross_amount),
    }
