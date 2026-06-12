import csv
from decimal import Decimal, InvalidOperation
from io import StringIO


class PayrollValidationError(Exception):
    pass


def _parse_decimal(value) -> Decimal:
    try:
        return Decimal(str(value or "0").replace(",", ""))
    except (InvalidOperation, TypeError):
        return Decimal("0")


def validate_payroll_against_csv(payroll_run, file_content: str) -> dict:
    """
    Bandingkan net_amount payslip sistem vs CSV legacy (kolom: employee_id, net_amount).
    Toleransi default Rp 0.
    """
    reader = csv.DictReader(StringIO(file_content))
    if not reader.fieldnames:
        raise PayrollValidationError("CSV kosong atau header tidak valid.")

    required = {"employee_id", "net_amount"}
    missing = required - set(reader.fieldnames)
    if missing:
        raise PayrollValidationError(f"Kolom wajib hilang: {', '.join(sorted(missing))}")

    expected = {}
    for row_num, row in enumerate(reader, start=2):
        eid = (row.get("employee_id") or "").strip()
        if not eid:
            continue
        expected[eid] = _parse_decimal(row.get("net_amount"))

    from apps.payroll.models import Payslip

    slips = Payslip.objects.filter(payroll_run=payroll_run).select_related("employee")
    actual = {s.employee.employee_id: s.net_amount for s in slips}

    mismatches = []
    missing_in_system = []
    missing_in_csv = []

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
            missing_in_csv.append(eid)

    return {
        "matched": len(expected) - len(mismatches) - len(missing_in_system),
        "mismatches": mismatches,
        "missing_in_system": missing_in_system,
        "missing_in_csv": missing_in_csv,
        "ok": not mismatches and not missing_in_system,
    }
