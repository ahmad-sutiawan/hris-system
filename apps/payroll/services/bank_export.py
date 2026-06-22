from apps.core.xlsx_io import write_xlsx

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


def export_bank_xlsx(payroll_run) -> bytes:
    def rows():
        for slip in payroll_run.payslips.select_related("employee"):
            emp = slip.employee
            yield [
                emp.employee_id,
                emp.full_name,
                emp.bank_name,
                emp.bank_account_number,
                emp.bank_account_name,
                slip.net_amount,
                payroll_run.period_start.isoformat(),
                payroll_run.period_end.isoformat(),
            ]

    return write_xlsx(BANK_EXPORT_HEADERS, rows())


export_bank_csv = export_bank_xlsx
