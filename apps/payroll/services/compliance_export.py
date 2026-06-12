import csv
from io import StringIO

from apps.payroll.models import Payslip


def export_bpjs_csv(payroll_run) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "employee_id",
            "full_name",
            "npwp",
            "bpjs_kesehatan",
            "bpjs_jht",
            "bpjs_jp",
            "gross_amount",
        ]
    )
    slips = Payslip.objects.filter(payroll_run=payroll_run).select_related("employee")
    for slip in slips:
        emp = slip.employee
        ded = slip.deductions_breakdown or {}
        writer.writerow(
            [
                emp.employee_id,
                emp.full_name,
                emp.npwp,
                ded.get("bpjs_kesehatan", "0"),
                ded.get("bpjs_jht", "0"),
                ded.get("bpjs_jp", "0"),
                slip.gross_amount,
            ]
        )
    return buffer.getvalue()


def export_pph21_csv(payroll_run) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "employee_id",
            "full_name",
            "tax_status",
            "npwp",
            "gross_amount",
            "pph21",
            "net_amount",
        ]
    )
    slips = Payslip.objects.filter(payroll_run=payroll_run).select_related("employee")
    for slip in slips:
        emp = slip.employee
        ded = slip.deductions_breakdown or {}
        writer.writerow(
            [
                emp.employee_id,
                emp.full_name,
                emp.tax_status,
                emp.npwp,
                slip.gross_amount,
                ded.get("pph21", "0"),
                slip.net_amount,
            ]
        )
    return buffer.getvalue()
