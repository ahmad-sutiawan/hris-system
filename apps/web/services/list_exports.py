"""CSV export row builders for list views."""

from apps.attendance.services.export import export_timesheets_csv
from apps.core.listing import format_date, format_dt, queryset_to_csv


EMPLOYEE_EXPORT_HEADERS = [
    "Employee ID",
    "Full Name",
    "NIK",
    "Email",
    "Phone",
    "Plant",
    "Branch",
    "Department",
    "Job Position",
    "Job Level",
    "Manager",
    "Gender",
    "Marital Status",
    "Birth Place",
    "Birth Date",
    "Address",
    "Mother Name",
    "Status",
    "Join Date",
]


COMPENSATION_EXPORT_HEADERS = [
    "Employee ID",
    "Full Name",
    "Plant",
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
]


def export_employee_compensation_csv(qs) -> str:
    def row(emp):
        return [
            emp.employee_id,
            emp.full_name,
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
        ]

    return queryset_to_csv(qs, COMPENSATION_EXPORT_HEADERS, row)


def export_employees_csv(qs) -> str:
    def row(emp):
        return [
            emp.employee_id,
            emp.full_name,
            emp.nik or "N/A",
            emp.email or "N/A",
            emp.phone or "N/A",
            emp.plant.code if emp.plant_id else "",
            emp.plant.get_branch_type_display() if emp.plant_id else "",
            emp.department.name if emp.department_id else "",
            emp.job_position.title if emp.job_position_id else "",
            emp.job_level.name if emp.job_level_id else "",
            emp.manager.full_name if emp.manager_id else "",
            emp.get_gender_display() if emp.gender else "N/A",
            emp.get_marital_status_display() if emp.marital_status else "N/A",
            emp.birth_place or "N/A",
            format_date(emp.birth_date) if emp.birth_date else "N/A",
            (emp.address or "N/A").replace("\n", " "),
            emp.mother_name or "N/A",
            emp.get_status_display(),
            format_date(emp.join_date),
        ]

    return queryset_to_csv(qs, EMPLOYEE_EXPORT_HEADERS, row)


SHIFT_EXPORT_HEADERS = [
    "Employee ID",
    "Employee Name",
    "Work Date",
    "Shift Code",
    "Shift Name",
    "Scheduled Check In",
    "Scheduled Check Out",
]


def export_shifts_csv(qs) -> str:
    def row(item):
        return [
            item.employee.employee_id,
            item.employee.full_name,
            format_date(item.work_date),
            item.shift.code,
            item.shift.name,
            item.scheduled_check_in.strftime("%H:%M") if item.scheduled_check_in else "",
            item.scheduled_check_out.strftime("%H:%M") if item.scheduled_check_out else "",
        ]

    return queryset_to_csv(qs, SHIFT_EXPORT_HEADERS, row)


class AttendanceExportError(Exception):
    pass


MAX_ATTENDANCE_EXPORT_DAYS = 366


def export_attendance_csv(qs) -> str:
    from apps.core.listing import MAX_EXPORT_ROWS

    return export_timesheets_csv(qs[:MAX_EXPORT_ROWS])


def export_attendance_csv_with_default_range(qs, *, date_from: str, date_to: str) -> str:
    from datetime import datetime, timedelta

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
    return export_attendance_csv(qs)


LEAVE_EXPORT_HEADERS = [
    "Employee ID",
    "Employee Name",
    "Leave Type",
    "Start Date",
    "End Date",
    "Days",
    "Status",
    "Reason",
    "Submitted At",
]


def export_leave_csv(qs) -> str:
    def row(item):
        return [
            item.employee.employee_id,
            item.employee.full_name,
            item.leave_type.name,
            format_date(item.start_date),
            format_date(item.end_date),
            str(item.days),
            item.get_status_display(),
            item.reason,
            format_dt(item.created_at),
        ]

    return queryset_to_csv(qs, LEAVE_EXPORT_HEADERS, row)


OVERTIME_EXPORT_HEADERS = [
    "Employee ID",
    "Employee Name",
    "Work Date",
    "Overtime Type",
    "OT Before (min)",
    "OT After (min)",
    "Compensation",
    "Leave Days Credited",
    "Status",
    "Reason",
    "Submitted At",
]


def export_overtime_csv(qs) -> str:
    def row(item):
        return [
            item.employee.employee_id,
            item.employee.full_name,
            format_date(item.work_date),
            item.overtime_type.name if item.overtime_type_id else "",
            item.ot_before_minutes,
            item.ot_after_minutes,
            item.get_compensation_mode_display(),
            item.leave_days_credited,
            item.get_status_display(),
            item.reason,
            format_dt(item.created_at),
        ]

    return queryset_to_csv(qs, OVERTIME_EXPORT_HEADERS, row)


PAYROLL_EXPORT_HEADERS = [
    "Plant",
    "Period Start",
    "Period End",
    "Status",
    "Notes",
    "Created At",
]


def export_payroll_runs_csv(qs) -> str:
    def row(item):
        return [
            item.plant.code,
            format_date(item.period_start),
            format_date(item.period_end),
            item.get_status_display(),
            item.notes,
            format_dt(item.created_at),
        ]

    return queryset_to_csv(qs, PAYROLL_EXPORT_HEADERS, row)


PAYSLIP_EXPORT_HEADERS = [
    "Employee ID",
    "Employee Name",
    "Plant",
    "Period Start",
    "Period End",
    "Gross",
    "Deduction",
    "Net",
]


def export_payslips_csv(qs) -> str:
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
        ]

    return queryset_to_csv(qs, PAYSLIP_EXPORT_HEADERS, row)


NOTIFICATION_EXPORT_HEADERS = [
    "Category",
    "Title",
    "Message",
    "Read",
    "Created At",
]


def export_notifications_csv(qs) -> str:
    def row(item):
        return [
            item.get_category_display(),
            item.title,
            item.message,
            "Yes" if item.is_read else "No",
            format_dt(item.created_at),
        ]

    return queryset_to_csv(qs, NOTIFICATION_EXPORT_HEADERS, row)


AUDIT_EXPORT_HEADERS = [
    "Timestamp",
    "User",
    "Action",
    "Model",
    "Object",
    "Changes",
]


def export_audit_csv(qs) -> str:
    def row(item):
        return [
            format_dt(item.created_at),
            item.user.username if item.user_id else "",
            item.action,
            item.model_name,
            item.object_repr,
            item.changes or "",
        ]

    return queryset_to_csv(qs, AUDIT_EXPORT_HEADERS, row)


def export_admin_resource_csv(resource, qs) -> str:
    headers = [col.header for col in resource.columns]

    def row(obj):
        from apps.web.admin_crud.queryset import get_cell_value

        return [get_cell_value(obj, col.attr) for col in resource.columns]

    return queryset_to_csv(qs, headers, row)
