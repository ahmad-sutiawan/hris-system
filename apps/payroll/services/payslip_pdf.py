from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.payroll.models import Payslip


def _fmt(amount):
    return f"Rp {amount:,.0f}".replace(",", ".")


def generate_payslip_pdf(payslip: Payslip) -> bytes:
    employee = payslip.employee
    run = payslip.payroll_run
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("SLIP GAJI", styles["Title"]))
    elements.append(Paragraph(f"Periode: {run.period_start} — {run.period_end}", styles["Normal"]))
    elements.append(Spacer(1, 8 * mm))

    info = [
        ["Employee ID", employee.employee_id],
        ["Nama", employee.full_name],
        ["Plant", run.plant.code],
        ["Department", employee.department.name if employee.department_id else "-"],
        ["NPWP", employee.npwp or "-"],
        ["Status Pajak", employee.tax_status or "-"],
        ["Verifikasi", payslip.verification_hash],
    ]
    info_table = Table(info, colWidths=[45 * mm, 120 * mm])
    info_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(info_table)
    elements.append(Spacer(1, 8 * mm))

    earnings_rows = [["Komponen Pendapatan", "Jumlah"]]
    for key, value in payslip.earnings_breakdown.items():
        label = key.replace("_", " ").title()
        earnings_rows.append([label, _fmt(float(value))])
    earnings_rows.append(["Total Bruto", _fmt(payslip.gross_amount)])

    earnings_table = Table(earnings_rows, colWidths=[100 * mm, 65 * mm])
    earnings_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(earnings_table)
    elements.append(Spacer(1, 6 * mm))

    deduction_rows = [["Komponen Potongan", "Jumlah"]]
    for key, value in payslip.deductions_breakdown.items():
        label = key.replace("_", " ").title()
        deduction_rows.append([label, _fmt(float(value))])
    deduction_rows.append(["Total Potongan", _fmt(payslip.deduction_amount)])

    deduction_table = Table(deduction_rows, colWidths=[100 * mm, 65 * mm])
    deduction_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7f1d1d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(deduction_table)
    elements.append(Spacer(1, 8 * mm))

    thp_table = Table(
        [["TAKE HOME PAY (THP)", _fmt(payslip.net_amount)]],
        colWidths=[100 * mm, 65 * mm],
    )
    thp_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#065f46")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(thp_table)

    doc.build(elements)
    return buffer.getvalue()
