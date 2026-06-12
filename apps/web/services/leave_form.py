from __future__ import annotations

from apps.employees.models import Employee
from apps.employees.services.onboarding import employee_leave_balances_summary
from apps.web.formatting import format_number


def serialize_leave_balance_rows(balances) -> list[dict]:
    return [
        {
            "code": balance.leave_type.code,
            "name": balance.leave_type.name,
            "remaining": format_number(balance.remaining, max_decimals=1),
            "pending": format_number(balance.pending, max_decimals=1),
            "used": format_number(balance.used, max_decimals=1),
        }
        for balance in balances
    ]


def _employee_label(employee: Employee) -> str:
    return f"{employee.full_name} ({employee.employee_id})"


def build_leave_balance_context(*, profile, show_employee_picker: bool, form) -> dict:
    """Build leave balance rows and optional per-employee map for the leave form."""
    if show_employee_picker:
        employees = list(form.fields["employee"].queryset)
        if profile and not any(employee.pk == profile.pk for employee in employees):
            employees.insert(0, profile)

        balances_by_employee: dict[str, list[dict]] = {}
        employee_labels: dict[str, str] = {}
        for employee in employees:
            key = str(employee.pk)
            rows = serialize_leave_balance_rows(employee_leave_balances_summary(employee))
            balances_by_employee[key] = rows
            employee_labels[key] = _employee_label(employee)

        selected = _resolve_selected_employee(form, profile, employees)
        selected_key = str(selected.pk) if selected else ""
        return {
            "leave_balance_rows": balances_by_employee.get(selected_key, []),
            "employee_label": employee_labels.get(selected_key, ""),
            "leave_balances_by_employee": balances_by_employee,
            "leave_employee_labels": employee_labels,
            "default_employee_id": selected_key,
        }

    rows = (
        serialize_leave_balance_rows(employee_leave_balances_summary(profile))
        if profile
        else []
    )
    return {
        "leave_balance_rows": rows,
        "employee_label": _employee_label(profile) if profile else "",
        "leave_balances_by_employee": {},
        "leave_employee_labels": {},
        "default_employee_id": str(profile.pk) if profile else "",
    }


def _resolve_selected_employee(form, profile, employees: list[Employee]) -> Employee | None:
    if form.is_bound:
        selected_id = form.data.get("employee")
        if selected_id:
            return next((employee for employee in employees if str(employee.pk) == selected_id), None)
        return profile

    if profile:
        return profile
    return employees[0] if employees else None
