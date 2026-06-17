from decimal import Decimal

# Simplified Indonesia payroll constants (MVP — update per regulasi)
BPJS_KES_EMPLOYEE_RATE = Decimal("0.01")
BPJS_KES_EMPLOYER_RATE = Decimal("0.04")
BPJS_KES_MAX_SALARY = Decimal("12000000")
BPJS_JHT_EMPLOYEE_RATE = Decimal("0.02")
BPJS_JP_EMPLOYEE_RATE = Decimal("0.01")
BPJS_JP_MAX_SALARY = Decimal("10547400")

# Legacy flat rates — replaced by TER master (PP 58/2023) when seeded.
TER_RATES = {
    "TK/0": Decimal("0"),
    "TK/1": Decimal("0.0025"),
    "K/0": Decimal("0"),
    "K/1": Decimal("0.0025"),
    "K/2": Decimal("0.005"),
    "K/3": Decimal("0.0075"),
}

OT_HOURLY_MULTIPLIER = Decimal("1.5")
WORKING_DAYS_PER_MONTH = Decimal("22")


def monthly_base(employee) -> Decimal:
    fixed = (
        employee.base_salary
        + employee.allowance_transport
        + employee.allowance_meal
        + employee.allowance_position
    )
    return fixed.quantize(Decimal("0.01"))


def effective_daily_wage(employee) -> Decimal:
    """Gaji harian efektif dari gaji pokok (daily langsung atau monthly/22)."""
    if employee.salary_scheme == employee.SalaryScheme.DAILY:
        return employee.base_salary
    return (employee.base_salary / WORKING_DAYS_PER_MONTH).quantize(Decimal("0.01"))


def daily_rate(employee) -> Decimal:
    return effective_daily_wage(employee).quantize(Decimal("0.01"))


def hourly_rate(employee) -> Decimal:
    return (daily_rate(employee) / Decimal("8")).quantize(Decimal("0.01"))


def calc_bpjs_kes(employee) -> Decimal:
    base = min(monthly_base(employee), BPJS_KES_MAX_SALARY)
    return (base * BPJS_KES_EMPLOYEE_RATE).quantize(Decimal("0.01"))


def calc_bpjs_jht(employee) -> Decimal:
    return (monthly_base(employee) * BPJS_JHT_EMPLOYEE_RATE).quantize(Decimal("0.01"))


def calc_bpjs_jp(employee) -> Decimal:
    base = min(monthly_base(employee), BPJS_JP_MAX_SALARY)
    return (base * BPJS_JP_EMPLOYEE_RATE).quantize(Decimal("0.01"))


def calc_pph21(gross: Decimal, employee) -> Decimal:
    if getattr(employee, "pph21_deduct", None) is False:
        return Decimal("0")
    tax_status = getattr(employee, "tax_status", "") or ""
    if not tax_status.strip():
        return Decimal("0")

    from apps.payroll.services.ter import lookup_ter_rate

    tenant = getattr(employee, "tenant", None) or getattr(employee, "tenant_id", None)
    if tenant is not None and not hasattr(tenant, "pk"):
        from apps.core.models import Tenant

        tenant = Tenant.objects.filter(pk=tenant).first()
    if tenant:
        rate = lookup_ter_rate(tenant=tenant, gross=gross, ptkp_code=tax_status)
    else:
        rate = TER_RATES.get(tax_status, Decimal("0"))
    return (gross * rate).quantize(Decimal("0.01"))


def calc_ot_pay(employee, ot_minutes: int, *, multiplier: Decimal | None = None) -> Decimal:
    if ot_minutes <= 0:
        return Decimal("0")
    hours = (Decimal(ot_minutes) / Decimal("60")).quantize(Decimal("0.01"))
    mult = multiplier if multiplier is not None else OT_HOURLY_MULTIPLIER
    return (hours * hourly_rate(employee) * mult).quantize(Decimal("0.01"))


def calc_daily_allowances(employee, *, present_days: int = 0) -> tuple[Decimal, dict]:
    """Tunjangan makan & transport × hari hadir (khusus skema daily)."""
    if employee.salary_scheme != employee.SalaryScheme.DAILY or present_days <= 0:
        return Decimal("0"), {}
    meal = (employee.allowance_meal * Decimal(present_days)).quantize(Decimal("0.01"))
    transport = (employee.allowance_transport * Decimal(present_days)).quantize(Decimal("0.01"))
    breakdown = {}
    if meal > 0:
        breakdown["allowance_meal"] = meal
    if transport > 0:
        breakdown["allowance_transport"] = transport
    return meal + transport, breakdown


def calc_period_base(employee, *, present_days: int = 0) -> Decimal:
    """Monthly fixed base, or daily rate × hari hadir for daily scheme."""
    if employee.salary_scheme == employee.SalaryScheme.DAILY:
        return (daily_rate(employee) * Decimal(present_days)).quantize(Decimal("0.01"))
    return monthly_base(employee)


def calc_alpha_deduction(employee, alpha_days: int) -> Decimal:
    return (daily_rate(employee) * Decimal(alpha_days)).quantize(Decimal("0.01"))


def aggregate_overtime_pay(employee, period_start, period_end) -> tuple[Decimal, dict]:
    """
    Hitung lembur dari pengajuan disetujui × menit timesheet × pengali jenis lembur.
    Mengembalikan (total, breakdown per kode jenis lembur).
    """
    from apps.attendance.models import DailyTimesheet, OvertimeRequest

    approved = OvertimeRequest.objects.filter(
        employee=employee,
        work_date__gte=period_start,
        work_date__lte=period_end,
        status=OvertimeRequest.Status.APPROVED,
        compensation_mode=OvertimeRequest.CompensationMode.CASH,
    ).select_related("overtime_type")

    total = Decimal("0")
    breakdown: dict[str, Decimal] = {}
    ot_before_total = Decimal("0")
    ot_after_total = Decimal("0")

    for req in approved:
        ts = DailyTimesheet.objects.filter(
            employee=employee,
            work_date=req.work_date,
        ).first()
        if not ts:
            continue

        ot_before = ts.ot_before_minutes
        ot_after = ts.ot_after_minutes
        if ot_before <= 0 and ot_after <= 0:
            continue

        multiplier = (
            req.overtime_type.multiplier
            if req.overtime_type_id
            else OT_HOURLY_MULTIPLIER
        )
        code = req.overtime_type.code if req.overtime_type_id else "OT"

        before_pay = calc_ot_pay(employee, ot_before, multiplier=multiplier)
        after_pay = calc_ot_pay(employee, ot_after, multiplier=multiplier)
        pay = before_pay + after_pay

        total += pay
        breakdown[code] = breakdown.get(code, Decimal("0")) + pay
        ot_before_total += before_pay
        ot_after_total += after_pay

    return total, {
        "by_type": breakdown,
        "ot_before": ot_before_total,
        "ot_after": ot_after_total,
    }
