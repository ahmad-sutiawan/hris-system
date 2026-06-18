from apps.attendance.models import AttendanceCode, AttendanceRecord, DailyTimesheet, OvertimeType
from apps.core.models import (
    Announcement,
    ApprovalLine,
    AuditLog,
    FeatureFlag,
    HolidayCalendar,
    Notification,
    Plant,
    PunchLocation,
    User,
)
from apps.employees.models import Employee, EmployeeDocument
from apps.leave.models import LeaveBalance, LeaveRequest, LeaveType
from apps.organization.models import Department, JobLevel, JobPosition
from apps.payroll.models import (
    PayrollRun,
    Payslip,
    Pph21TerBracket,
    Pph21TerCategory,
    Pph21TerPtkpMapping,
    SalaryComponent,
    ShiftAllowanceRate,
)
from apps.shifts.models import Shift, ShiftAssignment
from apps.web.admin_crud.forms import (
    AdminEmployeeForm,
    AdminLeaveRequestForm,
    AdminPayrollRunForm,
    AdminShiftAssignmentForm,
    AdminUserForm,
    AttendanceCodeForm,
    AttendanceRecordForm,
    OvertimeTypeForm,
    DailyTimesheetForm,
    DepartmentForm,
    EmployeeDocumentForm,
    FeatureFlagForm,
    JobPositionForm,
    LeaveBalanceForm,
    LeaveTypeForm,
    AnnouncementForm,
    ApprovalLineForm,
    HolidayCalendarForm,
    JobLevelForm,
    NotificationAdminForm,
    PayslipForm,
    PlantForm,
    PunchLocationForm,
    Pph21TerBracketForm,
    Pph21TerCategoryForm,
    Pph21TerPtkpMappingForm,
    SalaryComponentForm,
    ShiftAllowanceRateForm,
    ShiftForm,
)
from apps.web.admin_crud.registry import AdminResource, Column, register


def bootstrap_registry():
    # Tenant is kept as the DB root for all scoped data but is not exposed in
    # Admin Console — single-tenant deployments configure it via provisioning only.
    register(
        AdminResource(
            slug="plants",
            model=Plant,
            form_class=PlantForm,
            section="Core",
            title="Branch Name",
            title_plural="Branch Name",
            columns=[
                Column("Kode", "code"),
                Column("Branch Name", "name"),
                Column("Tipe Cabang", "branch_type"),
                Column("Lat", "latitude"),
                Column("Lng", "longitude"),
                Column("Radius (m)", "geo_fence_radius_m"),
                Column("Timezone", "timezone"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["code", "name"],
            select_related=["tenant"],
            order_by=["code"],
            tenant_scoped=False,
            master_data=True,
            master_group="Organization Structure",
            list_limit=500,
        )
    )
    register(
        AdminResource(
            slug="users",
            model=User,
            form_class=AdminUserForm,
            section="Core",
            title="Pengguna",
            title_plural="Users",
            columns=[
                Column("Username", "username"),
                Column("Email", "email"),
                Column("Role", "role"),
                Column("Plant", "plant"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["username", "email", "first_name", "last_name"],
            select_related=["tenant", "plant"],
            order_by=["username"],
            tenant_scoped=False,
        )
    )
    register(
        AdminResource(
            slug="feature-flags",
            model=FeatureFlag,
            form_class=FeatureFlagForm,
            section="Core",
            title="Feature Flag",
            title_plural="Feature Flags",
            columns=[
                Column("Key", "key"),
                Column("Plant", "plant"),
                Column("Enabled", "enabled"),
            ],
            search_fields=["key", "description"],
            select_related=["tenant", "plant"],
            order_by=["key"],
            tenant_scoped=True,
        )
    )
    register(
        AdminResource(
            slug="departments",
            model=Department,
            form_class=DepartmentForm,
            section="Organization",
            title="Organization",
            title_plural="Organization",
            columns=[
                Column("Organization", "name"),
                Column("Branch Name", "plant"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["code", "name"],
            select_related=["plant"],
            order_by=["name"],
            master_data=True,
            master_group="Organization Structure",
            list_limit=500,
        )
    )
    register(
        AdminResource(
            slug="job-positions",
            model=JobPosition,
            form_class=JobPositionForm,
            section="Organization",
            title="Job Position",
            title_plural="Job Position",
            columns=[
                Column("Kode", "code"),
                Column("Job Position", "title"),
                Column("Organization", "department"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["code", "title"],
            select_related=["department", "plant"],
            order_by=["title"],
            master_data=True,
            master_group="Organization Structure",
            list_limit=500,
        )
    )
    register(
        AdminResource(
            slug="pph21-ter-categories",
            model=Pph21TerCategory,
            form_class=Pph21TerCategoryForm,
            section="Payroll",
            title="Kategori TER PPh 21",
            title_plural="PPh 21 TER Categories",
            columns=[
                Column("Kode", "code"),
                Column("Nama", "name"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["code", "name"],
            order_by=["code"],
            master_data=True,
            master_group="Finance",
            list_limit=10,
        )
    )
    register(
        AdminResource(
            slug="pph21-ter-brackets",
            model=Pph21TerBracket,
            form_class=Pph21TerBracketForm,
            section="Payroll",
            title="Lapisan TER PPh 21",
            title_plural="PPh 21 TER Brackets",
            columns=[
                Column("Kategori", "category"),
                Column("No", "bracket_no"),
                Column("Dari", "income_from"),
                Column("Sampai", "income_to"),
                Column("Tarif", "rate"),
            ],
            search_fields=["category__code"],
            select_related=["category"],
            order_by=["category__code", "bracket_no"],
            master_data=True,
            master_group="Finance",
            list_limit=500,
        )
    )
    register(
        AdminResource(
            slug="pph21-ter-ptkp",
            model=Pph21TerPtkpMapping,
            form_class=Pph21TerPtkpMappingForm,
            section="Payroll",
            title="PTKP → TER",
            title_plural="PTKP → TER",
            columns=[
                Column("PTKP", "ptkp_code"),
                Column("Kategori TER", "category"),
            ],
            search_fields=["ptkp_code", "category__code"],
            select_related=["category"],
            order_by=["ptkp_code"],
            master_data=True,
            master_group="Finance",
            list_limit=20,
        )
    )
    register(
        AdminResource(
            slug="employees",
            model=Employee,
            form_class=AdminEmployeeForm,
            section="Employees",
            title="Karyawan",
            title_plural="Employees",
            columns=[
                Column("Employee ID", "employee_id"),
                Column("Full Name", "full_name"),
                Column("Status Employee", "status_employee"),
                Column("Organization", "department"),
                Column("Job Position", "job_position"),
                Column("Branch Name", "plant"),
                Column("PTKP Status", "tax_status"),
            ],
            search_fields=["employee_id", "full_name", "nik", "email", "tax_status"],
            select_related=["plant", "department"],
            order_by=["full_name"],
            hide_from_admin_nav=True,
        )
    )
    register(
        AdminResource(
            slug="employee-documents",
            model=EmployeeDocument,
            form_class=EmployeeDocumentForm,
            section="Employees",
            title="Dokumen Karyawan",
            title_plural="Employee Documents",
            columns=[
                Column("Karyawan", "employee"),
                Column("Tipe", "document_type"),
                Column("Kadaluarsa", "expiry_date"),
            ],
            search_fields=["employee__full_name", "employee__employee_id", "notes"],
            select_related=["employee"],
            order_by=["-created_at"],
        )
    )
    register(
        AdminResource(
            slug="shifts",
            model=Shift,
            form_class=ShiftForm,
            section="Shifts",
            title="Master Shift",
            title_plural="Master Shift",
            columns=[
                Column("Kode", "code"),
                Column("Nama", "name"),
                Column("Plant", "plant"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["code", "name"],
            select_related=["plant"],
            order_by=["code"],
            master_data=True,
            master_group="Operations",
            list_limit=500,
        )
    )
    register(
        AdminResource(
            slug="shift-assignments",
            model=ShiftAssignment,
            form_class=AdminShiftAssignmentForm,
            section="Shifts",
            title="Shift Assignment",
            title_plural="Shift Assignment",
            columns=[
                Column("Karyawan", "employee"),
                Column("Shift", "shift"),
                Column("Tanggal", "work_date"),
            ],
            search_fields=["employee__full_name", "employee__employee_id"],
            select_related=["employee", "shift"],
            order_by=["-work_date"],
            hide_from_admin_nav=True,
        )
    )
    register(
        AdminResource(
            slug="attendance-codes",
            model=AttendanceCode,
            form_class=AttendanceCodeForm,
            section="Attendance",
            title="Kode Absensi",
            title_plural="Attendance Codes",
            columns=[
                Column("Kode", "code"),
                Column("Label", "label"),
                Column("Payroll", "payroll_impact"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["code", "label"],
            order_by=["code"],
            master_data=True,
            master_group="Operations",
            list_limit=500,
        )
    )
    register(
        AdminResource(
            slug="overtime-types",
            model=OvertimeType,
            form_class=OvertimeTypeForm,
            section="Attendance",
            title="Jenis Lembur",
            title_plural="Overtime Types",
            columns=[
                Column("Kode", "code"),
                Column("Nama", "name"),
                Column("Kategori", "day_category"),
                Column("Jam", "hour_from"),
                Column("Pengali", "multiplier"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["code", "name"],
            order_by=["day_category", "hour_from", "code"],
            master_data=True,
            master_group="Operations",
            list_limit=500,
        )
    )
    register(
        AdminResource(
            slug="attendance-records",
            model=AttendanceRecord,
            form_class=AttendanceRecordForm,
            section="Attendance",
            title="Record Absensi",
            title_plural="Attendance Records",
            columns=[
                Column("Karyawan", "employee"),
                Column("Tanggal", "work_date"),
                Column("Clock In", "check_in"),
                Column("Clock Out", "check_out"),
            ],
            search_fields=["employee__full_name", "employee__employee_id"],
            select_related=["employee", "plant"],
            order_by=["-work_date"],
        )
    )
    register(
        AdminResource(
            slug="daily-timesheets",
            model=DailyTimesheet,
            form_class=DailyTimesheetForm,
            section="Attendance",
            title="Daily Timesheet",
            title_plural="Daily Timesheet",
            columns=[
                Column("Karyawan", "employee"),
                Column("Tanggal", "work_date"),
                Column("Shift", "shift_code"),
                Column("Paid Hrs", "paid_working_hours"),
            ],
            search_fields=["employee__full_name", "employee__employee_id", "shift_code"],
            select_related=["employee", "plant"],
            order_by=["-work_date"],
            hide_from_admin_nav=True,
        )
    )
    register(
        AdminResource(
            slug="leave-types",
            model=LeaveType,
            form_class=LeaveTypeForm,
            section="Leave",
            title="Jenis Cuti",
            title_plural="Leave Types",
            columns=[
                Column("Kode", "code"),
                Column("Nama", "name"),
                Column("Kuota", "default_quota_days"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["code", "name"],
            order_by=["code"],
            master_data=True,
            master_group="Operations",
            list_limit=500,
        )
    )
    register(
        AdminResource(
            slug="leave-balances",
            model=LeaveBalance,
            form_class=LeaveBalanceForm,
            section="Leave",
            title="Saldo Cuti",
            title_plural="Leave Balances",
            columns=[
                Column("Karyawan", "employee"),
                Column("Jenis", "leave_type"),
                Column("Tahun", "year"),
                Column("Sisa", "remaining"),
            ],
            search_fields=["employee__full_name", "employee__employee_id"],
            select_related=["employee", "leave_type"],
            order_by=["-year"],
        )
    )
    register(
        AdminResource(
            slug="leave-requests",
            model=LeaveRequest,
            form_class=AdminLeaveRequestForm,
            section="Leave",
            title="Pengajuan Cuti",
            title_plural="Leave Requests",
            columns=[
                Column("Karyawan", "employee"),
                Column("Jenis", "leave_type"),
                Column("Mulai", "start_date"),
                Column("Status", "status"),
            ],
            search_fields=["employee__full_name", "reason"],
            select_related=["employee", "leave_type"],
            order_by=["-created_at"],
            hide_from_admin_nav=True,
        )
    )
    register(
        AdminResource(
            slug="salary-components",
            model=SalaryComponent,
            form_class=SalaryComponentForm,
            section="Payroll",
            title="Komponen Gaji",
            title_plural="Salary Components",
            columns=[
                Column("Kode", "code"),
                Column("Nama", "name"),
                Column("Tipe", "component_type"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["code", "name"],
            order_by=["code"],
            master_data=True,
            master_group="Finance",
            list_limit=500,
        )
    )
    register(
        AdminResource(
            slug="shift-allowance-rates",
            model=ShiftAllowanceRate,
            form_class=ShiftAllowanceRateForm,
            section="Payroll",
            title="Tunjangan Shift",
            title_plural="Shift Allowances",
            columns=[
                Column("Kode", "code"),
                Column("Nama", "name"),
                Column("Nominal", "amount"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["code", "name"],
            order_by=["code"],
            master_data=True,
            master_group="Finance",
            tenant_scoped=True,
        )
    )
    register(
        AdminResource(
            slug="payroll-runs",
            model=PayrollRun,
            form_class=AdminPayrollRunForm,
            section="Payroll",
            title="Payroll Run",
            title_plural="Payroll Run",
            columns=[
                Column("Plant", "plant"),
                Column("Periode", "period_start"),
                Column("Status", "status"),
            ],
            search_fields=["notes"],
            select_related=["plant"],
            order_by=["-period_start"],
            hide_from_admin_nav=True,
        )
    )
    register(
        AdminResource(
            slug="payslips",
            model=Payslip,
            form_class=PayslipForm,
            section="Payroll",
            title="Payslip",
            title_plural="Payslip",
            columns=[
                Column("Karyawan", "employee"),
                Column("Payroll", "payroll_run"),
                Column("Net", "net_amount"),
            ],
            search_fields=["employee__full_name", "employee__employee_id"],
            select_related=["employee", "payroll_run"],
            order_by=["-pk"],
            hide_from_admin_nav=True,
        )
    )
    register(
        AdminResource(
            slug="audit-logs",
            model=AuditLog,
            form_class=NotificationAdminForm,
            section="Core",
            title="Audit Log",
            title_plural="Audit Logs",
            columns=[
                Column("Waktu", "created_at"),
                Column("User", "user"),
                Column("Aksi", "action"),
                Column("Model", "model_name"),
            ],
            search_fields=["model_name", "object_repr", "user__username"],
            select_related=["user"],
            order_by=["-created_at"],
            allow_create=False,
            allow_edit=False,
            allow_delete=False,
            tenant_scoped=True,
            list_limit=200,
        )
    )
    register(
        AdminResource(
            slug="announcements",
            model=Announcement,
            form_class=AnnouncementForm,
            section="Core",
            title="Pengumuman",
            title_plural="Announcements",
            columns=[
                Column("Judul", "title"),
                Column("Kategori", "category"),
                Column("Prioritas", "priority"),
                Column("Plant", "plant"),
                Column("Pin", "is_pinned"),
                Column("Aktif", "is_active"),
                Column("Mulai", "publish_start"),
                Column("Selesai", "publish_end"),
            ],
            search_fields=["title", "summary", "body"],
            select_related=["plant", "created_by"],
            order_by=["-is_pinned", "-publish_start"],
            allow_create=True,
            allow_edit=True,
            allow_delete=True,
            tenant_scoped=True,
        )
    )
    register(
        AdminResource(
            slug="admin-notifications",
            model=Notification,
            form_class=NotificationAdminForm,
            section="Core",
            title="Notifikasi (Admin)",
            title_plural="Notifications",
            columns=[
                Column("User", "user"),
                Column("Judul", "title"),
                Column("Kategori", "category"),
                Column("Dibaca", "is_read"),
            ],
            search_fields=["title", "message", "user__username"],
            select_related=["user"],
            order_by=["-created_at"],
            allow_create=True,
            tenant_scoped=True,
        )
    )
    register(
        AdminResource(
            slug="job-levels",
            model=JobLevel,
            form_class=JobLevelForm,
            section="Organization",
            title="Job Level",
            title_plural="Job Level",
            columns=[
                Column("Kode", "code"),
                Column("Nama", "name"),
                Column("Rank", "rank"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["code", "name"],
            order_by=["rank", "code"],
            master_data=True,
            master_group="Organization Structure",
            tenant_scoped=True,
        )
    )
    register(
        AdminResource(
            slug="punch-locations",
            model=PunchLocation,
            form_class=PunchLocationForm,
            section="Core",
            title="Lokasi Absen",
            title_plural="Punch Locations",
            columns=[
                Column("Plant", "plant"),
                Column("Nama", "name"),
                Column("Lat", "latitude"),
                Column("Lng", "longitude"),
                Column("Radius (m)", "radius_m"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["name", "plant__code"],
            select_related=["plant"],
            order_by=["plant__code", "name"],
            master_data=True,
            master_group="Attendance",
            tenant_scoped=True,
        )
    )
    register(
        AdminResource(
            slug="holidays",
            model=HolidayCalendar,
            form_class=HolidayCalendarForm,
            section="Core",
            title="Kalender Libur",
            title_plural="Holiday Calendar",
            columns=[
                Column("Tanggal", "holiday_date"),
                Column("Nama", "name"),
                Column("Tipe", "holiday_type"),
                Column("Plant", "plant"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["name"],
            select_related=["plant"],
            order_by=["-holiday_date"],
            master_data=True,
            master_group="Attendance",
            tenant_scoped=True,
        )
    )
    register(
        AdminResource(
            slug="approval-lines",
            model=ApprovalLine,
            form_class=ApprovalLineForm,
            section="Core",
            title="Approval Line",
            title_plural="Approval Lines",
            columns=[
                Column("Jenis", "request_type"),
                Column("Step", "step_order"),
                Column("Approver", "approver_kind"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["request_type"],
            order_by=["request_type", "step_order"],
            master_data=True,
            master_group="Workflow",
            tenant_scoped=True,
        )
    )
