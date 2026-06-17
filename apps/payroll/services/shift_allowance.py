"""Shift allowance earnings from timesheet shift codes."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from apps.attendance.models import DailyTimesheet
from apps.payroll.models import ShiftAllowanceRate


def bulk_shift_allowance_pay(
    employee_ids,
    period_start,
    period_end,
    *,
    tenant,
) -> dict[int, tuple[Decimal, dict[str, str]]]:
    """Return per-employee (total, earnings_breakdown) for shift allowances."""
    result = {eid: (Decimal("0"), {}) for eid in employee_ids}
    if not employee_ids:
        return result

    rates = {
        row.code: row.amount
        for row in ShiftAllowanceRate.objects.filter(tenant=tenant, is_active=True)
    }
    if not rates:
        return result

    counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    rows = DailyTimesheet.objects.filter(
        employee_id__in=employee_ids,
        work_date__gte=period_start,
        work_date__lte=period_end,
        check_in__isnull=False,
        shift__shift_allowance_code__gt="",
    ).values("employee_id", "shift__shift_allowance_code")

    for row in rows:
        code = row["shift__shift_allowance_code"]
        if code in rates:
            counts[row["employee_id"]][code] += 1

    for employee_id, code_counts in counts.items():
        total = Decimal("0")
        breakdown: dict[str, str] = {}
        for code, days in code_counts.items():
            amount = (rates[code] * Decimal(days)).quantize(Decimal("0.01"))
            if amount <= 0:
                continue
            breakdown[f"shift_allowance_{code.lower()}"] = str(amount)
            total += amount
        result[employee_id] = (total, breakdown)

    return result
