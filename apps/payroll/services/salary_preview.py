"""Estimasi perhitungan gaji untuk tampilan HR (halaman edit karyawan)."""

from decimal import Decimal

from apps.payroll.services.calculator import (
    BPJS_JHT_EMPLOYEE_RATE,
    BPJS_JP_EMPLOYEE_RATE,
    BPJS_JP_MAX_SALARY,
    BPJS_KES_EMPLOYEE_RATE,
    BPJS_KES_MAX_SALARY,
    WORKING_DAYS_PER_MONTH,
    calc_bpjs_jht,
    calc_bpjs_jp,
    calc_bpjs_kes,
    calc_daily_allowances,
    calc_pph21,
    calc_period_base,
    daily_rate,
    effective_daily_wage,
    monthly_base,
)
from apps.payroll.services.ter import preview_pph21, ter_category_for_ptkp
from apps.web.formatting import format_rupiah


def _amt_note(value) -> str:
    return format_rupiah(value).replace("Rp ", "")


def _line(key: str, label: str, amount: Decimal, *, note: str = "") -> dict:
    return {
        "key": key,
        "label": label,
        "amount": amount,
        "note": note,
    }


def build_salary_preview(employee, *, tenant, work_days: int | None = None) -> dict:
    """
    Simulasi satu periode gaji penuh (default 22 hari kerja, tanpa lembur & alpha)
    mengikuti logika ``calculate_payroll_run``.
    """
    days = work_days if work_days is not None else int(WORKING_DAYS_PER_MONTH)
    scheme = employee.salary_scheme
    is_daily = scheme == employee.SalaryScheme.DAILY

    earnings: list[dict] = []
    if is_daily:
        rate = daily_rate(employee)
        base = calc_period_base(employee, present_days=days)
        earnings.append(
            _line(
                "base_salary",
                "Upah harian × hari kerja",
                base,
                note=f"{_amt_note(rate)} × {days} hari",
            )
        )
        allowance_total, allowance_breakdown = calc_daily_allowances(
            employee, present_days=days
        )
        if allowance_breakdown.get("allowance_meal"):
            earnings.append(
                _line(
                    "allowance_meal",
                    "Tunjangan makan × hari",
                    allowance_breakdown["allowance_meal"],
                    note=f"{_amt_note(employee.allowance_meal)} × {days} hari",
                )
            )
        if allowance_breakdown.get("allowance_transport"):
            earnings.append(
                _line(
                    "allowance_transport",
                    "Tunjangan transport × hari",
                    allowance_breakdown["allowance_transport"],
                    note=f"{_amt_note(employee.allowance_transport)} × {days} hari",
                )
            )
        if employee.allowance_position > 0:
            earnings.append(
                _line(
                    "allowance_position",
                    "Tunjangan jabatan (basis BPJS)",
                    employee.allowance_position,
                    note="Tidak masuk bruto slip harian; dipakai dasar BPJS",
                )
            )
        gross = base + allowance_total
    else:
        base = monthly_base(employee)
        if employee.base_salary > 0:
            earnings.append(_line("base_salary", "Gaji pokok bulanan", employee.base_salary))
        if employee.allowance_transport > 0:
            earnings.append(
                _line("allowance_transport", "Tunjangan transport", employee.allowance_transport)
            )
        if employee.allowance_meal > 0:
            earnings.append(_line("allowance_meal", "Tunjangan makan", employee.allowance_meal))
        if employee.allowance_position > 0:
            earnings.append(
                _line("allowance_position", "Tunjangan jabatan", employee.allowance_position)
            )
        gross = base

    bpjs_base = monthly_base(employee)
    bpjs_kes = calc_bpjs_kes(employee)
    bpjs_jht = calc_bpjs_jht(employee)
    bpjs_jp = calc_bpjs_jp(employee)

    kes_base = min(bpjs_base, BPJS_KES_MAX_SALARY)
    jp_base = min(bpjs_base, BPJS_JP_MAX_SALARY)

    deductions: list[dict] = [
        _line(
            "bpjs_kesehatan",
            "BPJS Kesehatan (karyawan)",
            bpjs_kes,
            note=f"1% × min({_amt_note(bpjs_base)}, {_amt_note(BPJS_KES_MAX_SALARY)})",
        ),
        _line(
            "bpjs_jht",
            "BPJS JHT (karyawan)",
            bpjs_jht,
            note=f"2% × {_amt_note(bpjs_base)}",
        ),
        _line(
            "bpjs_jp",
            "BPJS JP (karyawan)",
            bpjs_jp,
            note=f"1% × min({_amt_note(bpjs_base)}, {_amt_note(BPJS_JP_MAX_SALARY)})",
        ),
    ]

    pph21 = Decimal("0")
    pph21_detail = None
    if employee.tax_status and getattr(employee, "pph21_deduct", None) is not False:
        pph21 = calc_pph21(gross, employee)
        pph21_detail = preview_pph21(
            tenant=tenant,
            gross=gross,
            ptkp_code=employee.tax_status,
        )
        rate_pct = pph21_detail["ter_rate_percent"]
        cat = pph21_detail["ter_category"] or "—"
        deductions.append(
            _line(
                "pph21",
                "PPh 21 (TER PP 58/2023)",
                pph21,
                note=f"PTKP {employee.tax_status} → TER {cat} · tarif {rate_pct}% × bruto",
            )
        )
    elif employee.tax_status and getattr(employee, "pph21_deduct", None) is False:
        pph21_detail = {
            "ptkp_code": employee.tax_status,
            "ter_category": ter_category_for_ptkp(tenant, employee.tax_status),
            "skipped": True,
        }
    else:
        pph21_detail = {"skipped": True, "reason": "PTKP belum diisi"}

    deductions_total = sum((d["amount"] for d in deductions), Decimal("0"))
    net = gross - deductions_total

    return {
        "scenario": f"Estimasi {days} hari kerja · tanpa lembur & potongan alpha",
        "salary_scheme": employee.get_salary_scheme_display(),
        "is_daily": is_daily,
        "daily_rate": effective_daily_wage(employee),
        "work_days": days,
        "bpjs_base": bpjs_base,
        "bpjs_kes_base": kes_base,
        "bpjs_jp_base": jp_base,
        "earnings": earnings,
        "gross": gross,
        "deductions": deductions,
        "deductions_total": deductions_total,
        "net": net,
        "pph21_detail": pph21_detail,
        "rates": {
            "bpjs_kes": BPJS_KES_EMPLOYEE_RATE * 100,
            "bpjs_jht": BPJS_JHT_EMPLOYEE_RATE * 100,
            "bpjs_jp": BPJS_JP_EMPLOYEE_RATE * 100,
        },
    }
