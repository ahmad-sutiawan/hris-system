import csv
from io import StringIO

BANK_EXPORT_HEADERS = [
    "employee_id",
    "employee_name",
    "bank_name",
    "bank_account_number",
    "bank_account_name",
    "net_amount",
    "period_start",
    "period_end",
]


def export_bank_csv(payroll_run):
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(BANK_EXPORT_HEADERS)
    for slip in payroll_run.payslips.select_related("employee"):
        emp = slip.employee
        writer.writerow(
            [
                emp.employee_id,
                emp.full_name,
                emp.bank_name,
                emp.bank_account_number,
                emp.bank_account_name,
                slip.net_amount,
                payroll_run.period_start.isoformat(),
                payroll_run.period_end.isoformat(),
            ]
        )
    return buffer.getvalue()
