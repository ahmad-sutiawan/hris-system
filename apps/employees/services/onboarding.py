from django.utils import timezone

from apps.attendance.services.timesheet import recalculate_daily_timesheet
from apps.employees.models import Employee
from apps.leave.models import LeaveBalance, LeaveType
from apps.leave.services.leave_workflow import get_or_create_balance
from apps.shifts.models import Shift, ShiftAssignment


def resolve_default_shift(employee: Employee) -> Shift | None:
    if employee.default_shift_id and employee.default_shift.is_active:
        return employee.default_shift

    plant = employee.plant
    if plant.default_shift_id and plant.default_shift.is_active:
        return plant.default_shift

    shift = Shift.objects.filter(
        tenant=employee.tenant,
        code="PAGI",
        is_active=True,
    ).first()
    if shift:
        return shift

    return (
        Shift.objects.filter(tenant=employee.tenant, is_active=True)
        .order_by("code")
        .first()
    )


def sync_employee_default_shift(employee: Employee, *, work_date=None) -> ShiftAssignment | None:
    shift = resolve_default_shift(employee)
    if not shift:
        return None

    work_date = work_date or timezone.localdate()
    assignment, _created = ShiftAssignment.objects.update_or_create(
        employee=employee,
        work_date=work_date,
        defaults={
            "tenant": employee.tenant,
            "shift": shift,
            "scheduled_check_in": shift.scheduled_check_in,
            "scheduled_check_out": shift.scheduled_check_out,
        },
    )
    recalculate_daily_timesheet(employee, work_date)
    return assignment


def assign_default_shift(employee: Employee, *, work_date=None) -> ShiftAssignment | None:
    work_date = work_date or employee.join_date or timezone.localdate()
    return sync_employee_default_shift(employee, work_date=work_date)


def provision_new_employee(
    employee: Employee,
    year: int | None = None,
    *,
    assign_shift: bool = False,
) -> list[LeaveBalance]:
    """Initialize leave balances and optionally assign default shift for new hires."""
    if employee.status in {Employee.Status.INACTIVE, Employee.Status.RESIGNED}:
        return []

    year = year or timezone.localdate().year
    balances = []
    leave_types = LeaveType.objects.filter(tenant=employee.tenant, is_active=True).order_by(
        "code"
    )
    for leave_type in leave_types:
        balances.append(get_or_create_balance(employee, leave_type, year=year))

    if assign_shift:
        assign_default_shift(employee)

    return balances


def employee_leave_balances_summary(employee: Employee, year: int | None = None) -> list[LeaveBalance]:
    """Ensure balances exist and return current-year rows for UI display."""
    year = year or timezone.localdate().year
    provision_new_employee(employee, year=year)
    return list(
        LeaveBalance.objects.filter(employee=employee, year=year)
        .select_related("leave_type")
        .order_by("leave_type__code")
    )
