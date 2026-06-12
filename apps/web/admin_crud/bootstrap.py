from apps.attendance.models import AttendanceCode, AttendanceRecord, DailyTimesheet, OvertimeType
from apps.core.models import AuditLog, FeatureFlag, Notification, Plant, Tenant, User
from apps.employees.models import Employee, EmployeeDocument
from apps.leave.models import LeaveBalance, LeaveHourlySegment, LeaveRequest, LeaveType
from apps.organization.models import Department, EmployeeGrade, JobPosition, LegalEntity
from apps.payroll.models import PayrollRun, Payslip, SalaryComponent, THRRun
from apps.shifts.models import Shift, ShiftAssignment, ShiftRotationTemplate
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
    EmployeeGradeForm,
    FeatureFlagForm,
    JobPositionForm,
    LeaveBalanceForm,
    LeaveHourlySegmentForm,
    LeaveTypeForm,
    LegalEntityForm,
    NotificationAdminForm,
    PayslipForm,
    PlantForm,
    SalaryComponentForm,
    ShiftForm,
    ShiftRotationTemplateForm,
    TenantForm,
    THRRunForm,
)
from apps.web.admin_crud.registry import AdminResource, Column, register


def bootstrap_registry():
    register(
        AdminResource(
            slug="tenants",
            model=Tenant,
            form_class=TenantForm,
            section="Core",
            title="Tenant",
            title_plural="Tenant",
            columns=[Column("Nama", "name"), Column("Slug", "slug"), Column("Aktif", "is_active")],
            search_fields=["name", "slug"],
            allow_create=False,
            allow_delete=False,
            tenant_scoped=False,
            order_by=["name"],
        )
    )
    register(
        AdminResource(
            slug="plants",
            model=Plant,
            form_class=PlantForm,
            section="Core",
            title="Plant",
            title_plural="Plant",
            columns=[
                Column("Kode", "code"),
                Column("Nama", "name"),
                Column("Timezone", "timezone"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["code", "name"],
            select_related=["tenant"],
            order_by=["code"],
            tenant_scoped=False,
            master_data=True,
            master_group="Struktur Organisasi",
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
            title_plural="Pengguna",
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
            slug="legal-entities",
            model=LegalEntity,
            form_class=LegalEntityForm,
            section="Organization",
            title="Legal Entity",
            title_plural="Legal Entity",
            columns=[Column("Nama", "name"), Column("NPWP", "npwp"), Column("Aktif", "is_active")],
            search_fields=["name", "npwp"],
            order_by=["name"],
            master_data=True,
            master_group="Struktur Organisasi",
            list_limit=500,
        )
    )
    register(
        AdminResource(
            slug="departments",
            model=Department,
            form_class=DepartmentForm,
            section="Organization",
            title="Department",
            title_plural="Department",
            columns=[
                Column("Kode", "code"),
                Column("Nama", "name"),
                Column("Plant", "plant"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["code", "name"],
            select_related=["plant"],
            order_by=["name"],
            master_data=True,
            master_group="Struktur Organisasi",
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
                Column("Jabatan", "title"),
                Column("Department", "department"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["code", "title"],
            select_related=["department", "plant"],
            order_by=["title"],
            master_data=True,
            master_group="Struktur Organisasi",
            list_limit=500,
        )
    )
    register(
        AdminResource(
            slug="employee-grades",
            model=EmployeeGrade,
            form_class=EmployeeGradeForm,
            section="Organization",
            title="Grade Karyawan",
            title_plural="Grade Karyawan",
            columns=[
                Column("Kode", "code"),
                Column("Nama", "name"),
                Column("Gaji Harian", "daily_wage"),
                Column("Plant", "plant"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["code", "name"],
            select_related=["plant"],
            order_by=["code"],
            master_data=True,
            master_group="Keuangan",
            list_limit=500,
        )
    )
    register(
        AdminResource(
            slug="employees",
            model=Employee,
            form_class=AdminEmployeeForm,
            section="Employees",
            title="Karyawan",
            title_plural="Karyawan",
            columns=[
                Column("ID", "employee_id"),
                Column("Nama", "full_name"),
                Column("Grade", "employee_grade"),
                Column("Skema Gaji", "salary_scheme"),
                Column("Plant", "plant"),
                Column("Status", "status"),
            ],
            search_fields=["employee_id", "full_name", "nik", "email", "employee_grade__code"],
            select_related=["plant", "department", "employee_grade"],
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
            title_plural="Dokumen Karyawan",
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
            master_group="Operasional",
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
            slug="shift-rotations",
            model=ShiftRotationTemplate,
            form_class=ShiftRotationTemplateForm,
            section="Shifts",
            title="Rotasi Shift",
            title_plural="Rotasi Shift",
            columns=[
                Column("Nama", "name"),
                Column("Plant", "plant"),
                Column("Siklus (minggu)", "cycle_weeks"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["name"],
            select_related=["plant"],
            order_by=["name"],
            master_data=True,
            master_group="Operasional",
            list_limit=500,
        )
    )
    register(
        AdminResource(
            slug="attendance-codes",
            model=AttendanceCode,
            form_class=AttendanceCodeForm,
            section="Attendance",
            title="Kode Absensi",
            title_plural="Kode Absensi",
            columns=[
                Column("Kode", "code"),
                Column("Label", "label"),
                Column("Payroll", "payroll_impact"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["code", "label"],
            order_by=["code"],
            master_data=True,
            master_group="Operasional",
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
            title_plural="Jenis Lembur",
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
            master_group="Operasional",
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
            title_plural="Record Absensi",
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
            title_plural="Jenis Cuti",
            columns=[
                Column("Kode", "code"),
                Column("Nama", "name"),
                Column("Kuota", "default_quota_days"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["code", "name"],
            order_by=["code"],
            master_data=True,
            master_group="Operasional",
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
            title_plural="Saldo Cuti",
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
            title_plural="Pengajuan Cuti",
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
            slug="leave-segments",
            model=LeaveHourlySegment,
            form_class=LeaveHourlySegmentForm,
            section="Leave",
            title="Segment Cuti (Jam)",
            title_plural="Segment Cuti (Jam)",
            columns=[
                Column("Pengajuan", "leave_request"),
                Column("Mulai", "start_time"),
                Column("Jam", "hours"),
            ],
            select_related=["leave_request"],
            order_by=["-pk"],
        )
    )
    register(
        AdminResource(
            slug="salary-components",
            model=SalaryComponent,
            form_class=SalaryComponentForm,
            section="Payroll",
            title="Komponen Gaji",
            title_plural="Komponen Gaji",
            columns=[
                Column("Kode", "code"),
                Column("Nama", "name"),
                Column("Tipe", "component_type"),
                Column("Aktif", "is_active"),
            ],
            search_fields=["code", "name"],
            order_by=["code"],
            master_data=True,
            master_group="Keuangan",
            list_limit=500,
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
            slug="thr-runs",
            model=THRRun,
            form_class=THRRunForm,
            section="Payroll",
            title="THR Run",
            title_plural="THR Run",
            columns=[
                Column("Plant", "plant"),
                Column("Tahun", "year"),
                Column("Status", "status"),
            ],
            select_related=["plant"],
            order_by=["-year"],
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
            slug="admin-notifications",
            model=Notification,
            form_class=NotificationAdminForm,
            section="Core",
            title="Notifikasi (Admin)",
            title_plural="Notifikasi",
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
