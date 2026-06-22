from decimal import Decimal, InvalidOperation

from apps.core.xlsx_io import read_xlsx_rows
from apps.payroll.models import Payslip


class PayrollValidationError(Exception):
    pass


def _parse_decimal(value) -> Decimal:
    try:
        return Decimal(str(value or "0").replace(",", ""))
    except (InvalidOperation, TypeError):
        return Decimal("0")


def validate_payroll_against_xlsx(payroll_run, file_bytes: bytes) -> dict:
    """Bandingkan net_amount payslip sistem vs file Excel legacy."""
    _, rows = read_xlsx_rows(file_bytes)
    if not rows:
        raise PayrollValidationError("File Excel kosong atau header tidak valid.")

    fieldnames = list(rows[0].keys())
    required = {"employee_id", "net_amount"}
    missing = required - set(fieldnames)
    if missing:
        raise PayrollValidationError(f"Kolom wajib hilang: {', '.join(sorted(missing))}")

    expected = {}
    for row_num, row in enumerate(rows, start=2):
        eid = str(row.get("employee_id") or "").strip()
        if not eid:
            continue
        expected[eid] = _parse_decimal(row.get("net_amount"))

    slips = Payslip.objects.filter(payroll_run=payroll_run).select_related("employee")
    actual = {s.employee.employee_id: s.net_amount for s in slips}

    mismatches = []
    missing_in_system = []
    missing_in_file = []

    for eid, exp_net in expected.items():
        act = actual.get(eid)
        if act is None:
            missing_in_system.append(eid)
            continue
        if act.quantize(Decimal("0.01")) != exp_net.quantize(Decimal("0.01")):
            mismatches.append(
                {
                    "employee_id": eid,
                    "expected": str(exp_net),
                    "actual": str(act),
                    "diff": str(act - exp_net),
                }
            )

    for eid in actual:
        if eid not in expected:
            missing_in_file.append(eid)

    return {
        "matched": len(expected) - len(mismatches) - len(missing_in_system),
        "mismatches": mismatches,
        "missing_in_system": missing_in_system,
        "missing_in_csv": missing_in_file,
        "ok": not mismatches and not missing_in_system,
    }


validate_payroll_against_csv = validate_payroll_against_xlsx
