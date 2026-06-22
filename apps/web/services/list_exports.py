"""Excel export row builders for list views."""

from apps.attendance.services.export import export_timesheets_xlsx
from apps.core.listing import format_date, format_dt
from apps.core.xlsx_io import write_xlsx
from apps.employees.talenta_vocabulary import TALENTA_COLUMNS


EMPLOYEE_EXPORT_HEADERS = list(TALENTA_COLUMNS)


COMPENSATION_EXPORT_HEADERS = [
    "Employee ID",
    "Full Name",
    "Plant",
    "Plant Code",
    "Salary Scheme",
    "Base Salary",
    "Allowance Transport",
    "Allowance Meal",
    "Allowance Position",
    "PTKP",
    "NPWP",
    "BPJS Kesehatan",
    "BPJS Ketenagakerjaan",
    "Bank",
    "Account Number",
    "Account Name",
    "Employee Tax Status",
    "Tax Config",
    "PPH21 Deduct",
]


def export_employee_compensation_xlsx(qs) -> bytes:
    def row(emp):
        return [
            emp.employee_id,
            emp.full_name,
            emp.plant.name if emp.plant_id else "",
            emp.plant.code if emp.plant_id else "",
            emp.get_salary_scheme_display(),
            emp.base_salary,
            emp.allowance_transport,
            emp.allowance_meal,
            emp.allowance_position,
            emp.tax_status or "N/A",
            emp.npwp or "N/A",
            emp.bpjs_kesehatan_number or "N/A",
            emp.bpjs_ketenagakerjaan_number or "N/A",
            emp.bank_name or "N/A",
            emp.bank_account_number or "N/A",
            emp.bank_account_name or "N/A",
            emp.employee_tax_status or "N/A",
            emp.tax_config or "N/A",
            emp.pph21_deduct,
        ]

    return write_xlsx(COMPENSATION_EXPORT_HEADERS, (row(emp) for emp in qs))


def export_employees_xlsx(qs) -> bytes:
    def row(emp):
        data = emp.talenta_export_row()
        barcode = getattr(emp, "barcode", "") or ""
        out = []
        for header in TALENTA_COLUMNS:
            if header == "Barcode":
                out.append(barcode)
            else:
                out.append(data.get(header, ""))
        return out

    return write_xlsx(TALENTA_COLUMNS, (row(emp) for emp in qs))


SHIFT_EXPORT_HEADERS = [
    "Employee ID",
    "Employee Name",
    "Work Date",
    "Shift Code",
    "Shift Name",
    "Scheduled Check In",
    "Scheduled Check Out",
    "Plant Code",
]


def export_shifts_xlsx(qs) -> bytes:
    def row(item):
        return [
            item.employee.employee_id,
            item.employee.full_name,
            format_date(item.work_date),
            item.shift.code,
            item.shift.name,
            item.scheduled_check_in.strftime("%H:%M") if item.scheduled_check_in else "",
            item.scheduled_check_out.strftime("%H:%M") if item.scheduled_check_out else "",
            item.employee.plant.code if item.employee.plant_id else "",
        ]

    return write_xlsx(SHIFT_EXPORT_HEADERS, (row(item) for item in qs))


class AttendanceExportError(Exception):
    pass


MAX_ATTENDANCE_EXPORT_DAYS = 366


def export_attendance_xlsx(qs) -> bytes:
    from apps.core.listing import MAX_EXPORT_ROWS

    return export_timesheets_xlsx(qs[:MAX_EXPORT_ROWS])


def export_attendance_xlsx_with_default_range(qs, *, date_from: str, date_to: str) -> bytes:
    from datetime import datetime

    from apps.core.listing import apply_date_field_range

    if not date_from or not date_to:
        raise AttendanceExportError(
            "Export rekap absensi memerlukan rentang tanggal (Dari dan Sampai)."
        )

    try:
        start = datetime.strptime(date_from, "%Y-%m-%d").date()
        end = datetime.strptime(date_to, "%Y-%m-%d").date()
    except ValueError as exc:
        raise AttendanceExportError("Format tanggal export tidak valid.") from exc

    if start > end:
        raise AttendanceExportError("Tanggal awal tidak boleh setelah tanggal akhir.")

    if (end - start).days > MAX_ATTENDANCE_EXPORT_DAYS:
        raise AttendanceExportError(
            f"Rentang export maksimal {MAX_ATTENDANCE_EXPORT_DAYS} hari."
        )

    qs = apply_date_field_range(qs, date_from=date_from, date_to=date_to, field_name="work_date")
    return export_attendance_xlsx(qs)


LEAVE_EXPORT_HEADERS = [
    "Employee ID",
    "Employee Name",
    "Leave Type",
    "Leave Type Code",
    "Start Date",
    "End Date",
    "Days",
    "Half Day",
    "Status",
    "Reason",
    "Approver",
    "Approved At",
    "Rejection Reason",
    "Approval Step",
    "Submitted At",
    "Updated At",
]


def export_leave_xlsx(qs) -> bytes:
    def row(item):
        return [
            item.employee.employee_id,
            item.employee.full_name,
            item.leave_type.name,
            item.leave_type.code,
            format_date(item.start_date),
            format_date(item.end_date),
            str(item.days),
            "Yes" if item.is_half_day else "No",
            item.get_status_display(),
            item.reason,
            item.approver.username if item.approver_id else "",
            format_dt(item.approved_at),
            item.rejection_reason,
            item.approval_step,
            format_dt(item.created_at),
            format_dt(item.updated_at),
        ]

    return write_xlsx(LEAVE_EXPORT_HEADERS, (row(item) for item in qs))


OVERTIME_EXPORT_HEADERS = [
    "Employee ID",
    "Employee Name",
    "Work Date",
    "Overtime Type",
    "Overtime Type Code",
    "OT Before (min)",
    "OT After (min)",
    "Compensation",
    "Leave Days Credited",
    "Status",
    "Reason",
    "Approver",
    "Approved At",
    "Rejection Reason",
    "Approval Step",
    "Submitted At",
    "Updated At",
]


def export_overtime_xlsx(qs) -> bytes:
    def row(item):
        return [
            item.employee.employee_id,
            item.employee.full_name,
            format_date(item.work_date),
            item.overtime_type.name if item.overtime_type_id else "",
            item.overtime_type.code if item.overtime_type_id else "",
            item.ot_before_minutes,
            item.ot_after_minutes,
            item.get_compensation_mode_display(),
            item.leave_days_credited,
            item.get_status_display(),
            item.reason,
            item.approver.username if item.approver_id else "",
            format_dt(item.approved_at),
            item.rejection_reason,
            item.approval_step,
            format_dt(item.created_at),
            format_dt(item.updated_at),
        ]

    return write_xlsx(OVERTIME_EXPORT_HEADERS, (row(item) for item in qs))


PAYROLL_EXPORT_HEADERS = [
    "Plant",
    "Period Start",
    "Period End",
    "Status",
    "Notes",
    "Finalized At",
    "Created At",
    "Updated At",
]


def export_payroll_runs_xlsx(qs) -> bytes:
    def row(item):
        return [
            item.plant.code,
            format_date(item.period_start),
            format_date(item.period_end),
            item.get_status_display(),
            item.notes,
            format_dt(item.finalized_at),
            format_dt(item.created_at),
            format_dt(item.updated_at),
        ]

    return write_xlsx(PAYROLL_EXPORT_HEADERS, (row(item) for item in qs))


PAYSLIP_EXPORT_HEADERS = [
    "Employee ID",
    "Employee Name",
    "Plant",
    "Period Start",
    "Period End",
    "Gross",
    "Deduction",
    "Net",
    "Earnings Breakdown",
    "Deductions Breakdown",
    "Verification Hash",
]


def export_payslips_xlsx(qs) -> bytes:
    def row(item):
        run = item.payroll_run
        return [
            item.employee.employee_id,
            item.employee.full_name,
            run.plant.code if run.plant_id else "",
            format_date(run.period_start),
            format_date(run.period_end),
            str(item.gross_amount),
            str(item.deduction_amount),
            str(item.net_amount),
            item.earnings_breakdown,
            item.deductions_breakdown,
            item.verification_hash,
        ]

    return write_xlsx(PAYSLIP_EXPORT_HEADERS, (row(item) for item in qs))


NOTIFICATION_EXPORT_HEADERS = [
    "Category",
    "Title",
    "Message",
    "Read",
    "Created At",
    "Updated At",
]


def export_notifications_xlsx(qs) -> bytes:
    def row(item):
        return [
            item.get_category_display(),
            item.title,
            item.message,
            "Yes" if item.is_read else "No",
            format_dt(item.created_at),
            format_dt(item.updated_at),
        ]

    return write_xlsx(NOTIFICATION_EXPORT_HEADERS, (row(item) for item in qs))


AUDIT_EXPORT_HEADERS = [
    "Timestamp",
    "User",
    "Action",
    "Model",
    "Object",
    "Changes",
    "IP Address",
    "User Agent",
]


def export_audit_xlsx(qs) -> bytes:
    def row(item):
        return [
            format_dt(item.created_at),
            item.user.username if item.user_id else "",
            item.action,
            item.model_name,
            item.object_repr,
            item.changes or "",
            item.ip_address or "",
            item.user_agent or "",
        ]

    return write_xlsx(AUDIT_EXPORT_HEADERS, (row(item) for item in qs))


def export_admin_resource_xlsx(resource, qs) -> bytes:
    headers = [col.header for col in resource.columns]

    def row(obj):
        from apps.web.admin_crud.queryset import get_cell_value

        return [get_cell_value(obj, col.attr) for col in resource.columns]

    return write_xlsx(headers, (row(obj) for obj in qs))


# Backward-compatible aliases.
export_employee_compensation_csv = export_employee_compensation_xlsx
export_employees_csv = export_employees_xlsx
export_shifts_csv = export_shifts_xlsx
export_attendance_csv = export_attendance_xlsx
export_attendance_csv_with_default_range = export_attendance_xlsx_with_default_range
export_leave_csv = export_leave_xlsx
export_overtime_csv = export_overtime_xlsx
export_payroll_runs_csv = export_payroll_runs_xlsx
export_payslips_csv = export_payslips_xlsx
export_notifications_csv = export_notifications_xlsx
export_audit_csv = export_audit_xlsx
export_admin_resource_csv = export_admin_resource_xlsx
