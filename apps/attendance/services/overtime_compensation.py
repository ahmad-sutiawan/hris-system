from __future__ import annotations

from decimal import Decimal

from apps.attendance.models import OvertimeRequest
from apps.leave.models import LeaveBalance, LeaveType
from apps.leave.services.leave_workflow import get_or_create_balance
from apps.payroll.services.calculator import calc_ot_pay, hourly_rate
from apps.web.formatting import format_number

OT_LEAVE_MINUTES_PER_DAY = 480
OT_LEAVE_TYPE_CODE = "CL"
OT_LEAVE_TYPE_NAME = "Cuti dari Lembur"


def total_overtime_minutes(*, ot_before_minutes: int, ot_after_minutes: int) -> int:
    return max(0, ot_before_minutes) + max(0, ot_after_minutes)


def overtime_minutes_to_leave_days(total_minutes: int) -> Decimal:
    if total_minutes <= 0:
        return Decimal("0")
    return (Decimal(total_minutes) / Decimal(OT_LEAVE_MINUTES_PER_DAY)).quantize(Decimal("0.01"))


def estimate_cash_compensation(
    employee,
    *,
    ot_before_minutes: int,
    ot_after_minutes: int,
    overtime_type=None,
) -> Decimal:
    multiplier = (
        overtime_type.multiplier
        if overtime_type is not None
        else Decimal("1.5")
    )
    before_pay = calc_ot_pay(employee, ot_before_minutes, multiplier=multiplier)
    after_pay = calc_ot_pay(employee, ot_after_minutes, multiplier=multiplier)
    return before_pay + after_pay


def build_compensation_preview(
    employee,
    *,
    ot_before_minutes: int,
    ot_after_minutes: int,
    overtime_type=None,
) -> dict:
    total_minutes = total_overtime_minutes(
        ot_before_minutes=ot_before_minutes,
        ot_after_minutes=ot_after_minutes,
    )
    leave_days = overtime_minutes_to_leave_days(total_minutes)
    cash_amount = estimate_cash_compensation(
        employee,
        ot_before_minutes=ot_before_minutes,
        ot_after_minutes=ot_after_minutes,
        overtime_type=overtime_type,
    )
    return {
        "total_minutes": total_minutes,
        "leave_days": format_number(leave_days, max_decimals=2),
        "cash_amount": format_number(cash_amount, money=True),
        "hourly_rate": format_number(hourly_rate(employee), money=True),
        "grade_label": (
            "Gaji harian"
            if employee.salary_scheme == employee.SalaryScheme.DAILY
            else "Gaji pokok ÷ 22"
        ),
    }


def get_or_create_overtime_leave_type(tenant) -> LeaveType:
    leave_type, _ = LeaveType.objects.get_or_create(
        tenant=tenant,
        code=OT_LEAVE_TYPE_CODE,
        defaults={
            "name": OT_LEAVE_TYPE_NAME,
            "is_paid": True,
            "default_quota_days": Decimal("0"),
            "is_active": True,
        },
    )
    return leave_type


def credit_overtime_as_leave(overtime_request: OvertimeRequest) -> LeaveBalance:
    total_minutes = total_overtime_minutes(
        ot_before_minutes=overtime_request.ot_before_minutes,
        ot_after_minutes=overtime_request.ot_after_minutes,
    )
    leave_days = overtime_minutes_to_leave_days(total_minutes)
    if leave_days <= 0:
        raise ValueError("Durasi lembur tidak cukup untuk dikonversi ke cuti.")

    leave_type = get_or_create_overtime_leave_type(overtime_request.tenant)
    year = overtime_request.work_date.year
    balance = get_or_create_balance(overtime_request.employee, leave_type, year=year)
    balance.accrued += leave_days
    balance.remaining += leave_days
    balance.save(update_fields=["accrued", "remaining", "updated_at"])

    overtime_request.leave_days_credited = leave_days
    overtime_request.save(update_fields=["leave_days_credited", "updated_at"])
    return balance
