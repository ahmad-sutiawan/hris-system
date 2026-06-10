from decimal import Decimal

# Simplified Indonesia payroll constants (MVP — update per regulasi)
BPJS_KES_EMPLOYEE_RATE = Decimal("0.01")
BPJS_KES_EMPLOYER_RATE = Decimal("0.04")
BPJS_KES_MAX_SALARY = Decimal("12000000")
BPJS_JHT_EMPLOYEE_RATE = Decimal("0.02")
BPJS_JP_EMPLOYEE_RATE = Decimal("0.01")
BPJS_JP_MAX_SALARY = Decimal("10547400")

# Simplified TER monthly rates by tax status (MVP placeholder)
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


def daily_rate(employee) -> Decimal:
    base = monthly_base(employee)
    if employee.salary_scheme == employee.SalaryScheme.DAILY:
        return employee.base_salary
    return (base / WORKING_DAYS_PER_MONTH).quantize(Decimal("0.01"))


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


def calc_pph21(gross: Decimal, tax_status: str) -> Decimal:
    rate = TER_RATES.get(tax_status or "TK/0", Decimal("0"))
    return (gross * rate).quantize(Decimal("0.01"))


def calc_ot_pay(employee, ot_after_minutes: int) -> Decimal:
    if ot_after_minutes <= 0:
        return Decimal("0")
    hours = (Decimal(ot_after_minutes) / Decimal("60")).quantize(Decimal("0.01"))
    return (hours * hourly_rate(employee) * OT_HOURLY_MULTIPLIER).quantize(Decimal("0.01"))


def calc_alpha_deduction(employee, alpha_days: int) -> Decimal:
    return (daily_rate(employee) * Decimal(alpha_days)).quantize(Decimal("0.01"))
