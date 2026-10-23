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


def ensure_leave_balances(
    employee: Employee,
    year: int | None = None,
) -> list[LeaveBalance]:
    """Pastikan saldo cuti tahun berjalan ada (tanpa menyentuh akun login)."""
    if employee.status in {Employee.Status.INACTIVE, Employee.Status.RESIGNED}:
        return []

    year = year or timezone.localdate().year
    balances = []
    leave_types = LeaveType.objects.filter(tenant=employee.tenant, is_active=True).order_by(
        "code"
    )
    for leave_type in leave_types:
        balances.append(get_or_create_balance(employee, leave_type, year=year))
    return balances


def provision_imported_employees(employees: list[Employee]) -> None:
    """Saldo cuti, shift, dan akun login untuk karyawan yang baru diimpor.

    Timesheet tidak dihitung di sini. Perhitungan tetap jalan saat absensi atau rekap.
    """
    if not employees:
        return
    _bulk_leave_balances(employees)
    _bulk_shift_assignments(employees)
    _bulk_login_accounts(employees)


def _bulk_leave_balances(employees: list[Employee]) -> None:
    year = timezone.localdate().year
    tenant = employees[0].tenant
    active = [
        employee
        for employee in employees
        if employee.status not in {Employee.Status.INACTIVE, Employee.Status.RESIGNED}
    ]
    if not active:
        return
    leave_types = list(
        LeaveType.objects.filter(tenant=tenant, is_active=True).order_by("code")
    )
    if not leave_types:
        return
    balances = []
    for employee in active:
        for leave_type in leave_types:
            quota = leave_type.default_quota_days
            balances.append(
                LeaveBalance(
                    tenant=employee.tenant,
                    employee=employee,
                    leave_type=leave_type,
                    year=year,
                    opening_balance=quota,
                    accrued=quota,
                    remaining=quota,
                )
            )
    LeaveBalance.objects.bulk_create(balances, ignore_conflicts=True)


def _bulk_shift_assignments(employees: list[Employee]) -> None:
    from apps.core.models import Plant

    tenant = employees[0].tenant
    pagi = Shift.objects.filter(tenant=tenant, code="PAGI", is_active=True).first()
    fallback = None
    if pagi is None:
        fallback = (
            Shift.objects.filter(tenant=tenant, is_active=True).order_by("code").first()
        )
    plants = {
        plant.pk: plant
        for plant in Plant.objects.filter(
            pk__in={employee.plant_id for employee in employees if employee.plant_id}
        ).select_related("default_shift")
    }
    assignments = []
    today = timezone.localdate()
    for employee in employees:
        shift = None
        if employee.default_shift_id and getattr(employee.default_shift, "is_active", False):
            shift = employee.default_shift
        else:
            plant = plants.get(employee.plant_id)
            if plant and plant.default_shift_id and plant.default_shift.is_active:
                shift = plant.default_shift
            else:
                shift = pagi or fallback
        if shift is None:
            continue
        assignments.append(
            ShiftAssignment(
                tenant=employee.tenant,
                employee=employee,
                shift=shift,
                work_date=employee.join_date or today,
                scheduled_check_in=shift.scheduled_check_in,
                scheduled_check_out=shift.scheduled_check_out,
            )
        )
    if assignments:
        ShiftAssignment.objects.bulk_create(assignments, ignore_conflicts=True)


def _bulk_login_accounts(employees: list[Employee]) -> None:
    from apps.core.auth_login import apply_employee_credentials, employee_login_password
    from apps.core.models import User

    pending = [employee for employee in employees if employee.employee_id and not employee.user_id]
    if not pending:
        return

    wanted = [employee.employee_id for employee in pending]
    taken = {
        username.casefold()
        for username in User.objects.filter(username__in=wanted).values_list("username", flat=True)
    }
    fresh = []
    for employee in pending:
        if employee.employee_id.casefold() in taken:
            apply_employee_credentials(employee)
            continue
        user = User(
            username=employee.employee_id,
            tenant=employee.tenant,
            plant=employee.plant,
            role=User.Role.EMPLOYEE,
            is_active=True,
        )
        user.set_password(employee_login_password(employee))
        fresh.append((employee, user))
        taken.add(employee.employee_id.casefold())

    if not fresh:
        return

    User.objects.bulk_create([user for _, user in fresh])
    created = {
        user.username.casefold(): user
        for user in User.objects.filter(username__in=[user.username for _, user in fresh])
    }
    linked = []
    for employee, user in fresh:
        employee.user = created[user.username.casefold()]
        linked.append(employee)
    Employee.objects.bulk_update(linked, ["user"])


def provision_new_employee(
    employee: Employee,
    year: int | None = None,
    *,
    assign_shift: bool = False,
    sync_credentials: bool = False,
) -> list[LeaveBalance]:
    """Initialize leave balances and optionally assign default shift for new hires."""
    balances = ensure_leave_balances(employee, year=year)

    if assign_shift:
        assign_default_shift(employee)

    if sync_credentials and employee.employee_id:
        from apps.core.auth_login import apply_employee_credentials
        from apps.core.models import User

        role = None
        if employee.user_id and employee.user.role == User.Role.MANAGER:
            role = User.Role.MANAGER
        apply_employee_credentials(employee, role=role)

    return balances


def employee_leave_balances_summary(employee: Employee, year: int | None = None) -> list[LeaveBalance]:
    """Ensure balances exist and return current-year rows for UI display."""
    year = year or timezone.localdate().year
    ensure_leave_balances(employee, year=year)
    return list(
        LeaveBalance.objects.filter(employee=employee, year=year)
        .select_related("leave_type")
        .order_by("leave_type__code")
    )
