from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.attendance.models import DailyTimesheet
from apps.employees.models import Employee
from apps.employees.services.onboarding import employee_leave_balances_summary, resolve_default_shift
from apps.payroll.models import PayrollRun, Payslip
from apps.payroll.services.calculator import daily_rate, hourly_rate
from apps.shifts.models import ShiftAssignment


def _month_bounds(reference_date=None):
    today = reference_date or timezone.localdate()
    return today.replace(day=1), today


def build_employee_profile_context(employee: Employee) -> dict:
    today = timezone.localdate()
    month_start, month_end = _month_bounds(today)

    employee = (
        Employee.objects.select_related(
            "plant",
            "department",
            "job_position",
            "manager",
            "legal_entity",
            "default_shift",
            "user",
        )
        .get(pk=employee.pk)
    )

    today_assignment = (
        ShiftAssignment.objects.filter(employee=employee, work_date=today)
        .select_related("shift")
        .first()
    )
    upcoming_shifts = list(
        ShiftAssignment.objects.filter(
            employee=employee,
            work_date__gte=today,
            work_date__lte=today + timedelta(days=13),
        )
        .select_related("shift")
        .order_by("work_date")[:14]
    )

    today_timesheet = (
        DailyTimesheet.objects.filter(employee=employee, work_date=today)
        .select_related("attendance_code")
        .first()
    )
    month_timesheets = DailyTimesheet.objects.filter(
        employee=employee,
        work_date__gte=month_start,
        work_date__lte=month_end,
    ).select_related("attendance_code", "shift")

    month_stats = {
        "present_days": month_timesheets.filter(check_in__isnull=False)
        .exclude(attendance_code__code="A")
        .count(),
        "paid_hours": sum(ts.paid_working_hours for ts in month_timesheets),
        "late_minutes": sum(ts.late_in_minutes for ts in month_timesheets),
        "ot_before_minutes": sum(ts.ot_before_minutes for ts in month_timesheets),
        "ot_after_minutes": sum(ts.ot_after_minutes for ts in month_timesheets),
        "alpha_days": month_timesheets.filter(attendance_code__code="A").count(),
    }

    recent_timesheets = list(
        DailyTimesheet.objects.filter(
            employee=employee,
            work_date__gte=today - timedelta(days=13),
            work_date__lte=today,
        )
        .select_related("attendance_code")
        .order_by("-work_date")[:14]
    )

    leave_balances = employee_leave_balances_summary(employee)
    latest_payslip = (
        Payslip.objects.filter(
            employee=employee,
            payroll_run__status=PayrollRun.Status.FINALIZED,
        )
        .select_related("payroll_run")
        .order_by("-payroll_run__period_end")
        .first()
    )

    total_compensation = (
        employee.base_salary
        + employee.allowance_transport
        + employee.allowance_meal
        + employee.allowance_position
    ).quantize(Decimal("0.01"))

    return {
        "employee": employee,
        "today": today,
        "month_start": month_start,
        "month_end": month_end,
        "today_assignment": today_assignment,
        "upcoming_shifts": upcoming_shifts,
        "default_shift": resolve_default_shift(employee),
        "today_timesheet": today_timesheet,
        "month_stats": month_stats,
        "recent_timesheets": recent_timesheets,
        "leave_balances": leave_balances,
        "latest_payslip": latest_payslip,
        "total_compensation": total_compensation,
        "effective_daily_wage": daily_rate(employee),
        "effective_hourly_wage": hourly_rate(employee),
    }
