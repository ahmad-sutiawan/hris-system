from django import forms
from django.contrib.auth import get_user_model

from apps.attendance.models import AttendanceCode, AttendanceRecord, DailyTimesheet, OvertimeType
from apps.core.models import FeatureFlag, Notification, Plant, Tenant
from apps.employees.models import Employee, EmployeeDocument
from apps.leave.models import LeaveBalance, LeaveHourlySegment, LeaveRequest, LeaveType
from apps.organization.models import Department, EmployeeGrade, JobPosition, LegalEntity
from apps.payroll.models import PayrollRun, Payslip, SalaryComponent, THRRun
from apps.shifts.models import Shift, ShiftAssignment, ShiftRotationTemplate
from apps.web.forms import (
    HRIS_INPUT_CLASS,
    HRIS_SELECT_CLASS,
    HRIS_TEXTAREA_CLASS,
    _filter_plant_queryset,
    _style_fields,
)
from apps.web.widgets import apply_date_fields
from apps.employees.services.user_link import available_users_for_employee

User = get_user_model()


def _base_init(form, tenant=None, user=None):
    _style_fields(form)
    if tenant and hasattr(form, "fields") and "tenant" in form.fields:
        form.fields["tenant"].queryset = Tenant.objects.filter(pk=tenant.pk)
        form.fields["tenant"].initial = tenant
        form.fields["tenant"].widget = forms.HiddenInput()
    if tenant:
        _filter_plant_queryset(form, tenant, user)
    if tenant and "plant" in form.fields and user and not user.is_admin and user.plant_id:
        form.fields["plant"].queryset = form.fields["plant"].queryset.filter(pk=user.plant_id)


class TenantForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ["name", "slug", "is_active"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)


class PlantForm(forms.ModelForm):
    class Meta:
        model = Plant
        fields = [
            "tenant",
            "code",
            "name",
            "timezone",
            "address",
            "geo_fence_radius_m",
            "default_shift",
            "is_active",
        ]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _base_init(self, tenant, user)
        if tenant:
            self.fields["tenant"].queryset = Tenant.objects.filter(pk=tenant.pk)
            self.fields["default_shift"].queryset = Shift.objects.filter(
                tenant=tenant, is_active=True
            )
            self.fields["default_shift"].required = False


class FeatureFlagForm(forms.ModelForm):
    class Meta:
        model = FeatureFlag
        fields = ["tenant", "plant", "key", "enabled", "description"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _base_init(self, tenant, user)
        if tenant:
            self.fields["tenant"].queryset = Tenant.objects.filter(pk=tenant.pk)


class AdminUserForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        required=False,
        widget=forms.PasswordInput(attrs={"class": HRIS_INPUT_CLASS, "autocomplete": "new-password"}),
        help_text="Kosongkan jika tidak ingin mengubah password.",
    )
    password2 = forms.CharField(
        label="Konfirmasi password",
        required=False,
        widget=forms.PasswordInput(attrs={"class": HRIS_INPUT_CLASS, "autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "tenant",
            "plant",
            "is_active",
            "is_staff",
        ]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        self._creating = kwargs.get("instance") is None
        super().__init__(*args, **kwargs)
        _base_init(self, tenant, user)
        if tenant:
            self.fields["tenant"].queryset = Tenant.objects.filter(pk=tenant.pk)
            self.fields["tenant"].initial = tenant
        if self._creating:
            self.fields["password1"].required = True
            self.fields["password2"].required = True

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "Password tidak cocok.")
        elif self._creating:
            self.add_error("password1", "Password wajib untuk user baru.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class LegalEntityForm(forms.ModelForm):
    class Meta:
        model = LegalEntity
        fields = ["name", "npwp", "is_active"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["plant", "code", "name", "parent", "is_active"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _base_init(self, tenant, user)
        if tenant:
            self.fields["parent"].queryset = Department.objects.filter(tenant=tenant)


class JobPositionForm(forms.ModelForm):
    class Meta:
        model = JobPosition
        fields = ["plant", "department", "code", "title", "is_active"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _base_init(self, tenant, user)
        if tenant:
            self.fields["department"].queryset = Department.objects.filter(tenant=tenant)


class EmployeeGradeForm(forms.ModelForm):
    class Meta:
        model = EmployeeGrade
        fields = ["plant", "code", "name", "daily_wage", "description", "is_active"]
        labels = {
            "daily_wage": "Gaji harian",
            "code": "Kode grade",
            "name": "Nama grade",
        }

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _base_init(self, tenant, user)


class AdminEmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            "employee_id",
            "full_name",
            "nik",
            "email",
            "phone",
            "plant",
            "legal_entity",
            "department",
            "job_position",
            "employee_grade",
            "manager",
            "user",
            "join_date",
            "contract_end_date",
            "resign_date",
            "status",
            "salary_scheme",
            "base_salary",
            "allowance_transport",
            "allowance_meal",
            "allowance_position",
            "tax_status",
            "npwp",
            "bpjs_kesehatan_number",
            "bpjs_ketenagakerjaan_number",
            "bank_name",
            "bank_account_number",
            "bank_account_name",
        ]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        apply_date_fields(self, "join_date", "contract_end_date", "resign_date")
        _base_init(self, tenant, user)
        if tenant:
            from apps.organization.models import Department, JobPosition

            self.fields["legal_entity"].queryset = LegalEntity.objects.filter(tenant=tenant)
            self.fields["department"].queryset = Department.objects.filter(tenant=tenant)
            self.fields["job_position"].queryset = JobPosition.objects.filter(tenant=tenant)
            self.fields["employee_grade"].queryset = EmployeeGrade.objects.filter(
                tenant=tenant, is_active=True
            )
            self.fields["employee_grade"].required = False
            self.fields["manager"].queryset = Employee.objects.filter(tenant=tenant).exclude(
                status__in=[Employee.Status.INACTIVE, Employee.Status.RESIGNED]
            )
            current_user_id = self.instance.user_id if self.instance.pk else None
            self.fields["user"].queryset = available_users_for_employee(tenant, current_user_id)
            self.fields["user"].required = False
            if self.instance.pk:
                self.fields["manager"].queryset = self.fields["manager"].queryset.exclude(
                    pk=self.instance.pk
                )


class EmployeeDocumentForm(forms.ModelForm):
    class Meta:
        model = EmployeeDocument
        fields = ["employee", "document_type", "file", "expiry_date", "notes"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        apply_date_fields(self, "expiry_date")
        if tenant:
            self.fields["employee"].queryset = Employee.objects.filter(tenant=tenant)


class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = [
            "plant",
            "name",
            "code",
            "label",
            "scheduled_check_in",
            "scheduled_check_out",
            "break_minutes",
            "grace_period_minutes",
            "schedule_working_hours",
            "cross_day",
            "shift_allowance_code",
            "is_active",
        ]
        widgets = {
            "scheduled_check_in": forms.TimeInput(attrs={"type": "time", "class": HRIS_INPUT_CLASS}),
            "scheduled_check_out": forms.TimeInput(attrs={"type": "time", "class": HRIS_INPUT_CLASS}),
        }

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        _base_init(self, tenant, user)


class AdminShiftAssignmentForm(forms.ModelForm):
    class Meta:
        model = ShiftAssignment
        fields = ["employee", "shift", "work_date", "scheduled_check_in", "scheduled_check_out"]
        widgets = {
            "scheduled_check_in": forms.TimeInput(attrs={"type": "time", "class": HRIS_INPUT_CLASS}),
            "scheduled_check_out": forms.TimeInput(attrs={"type": "time", "class": HRIS_INPUT_CLASS}),
        }

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        apply_date_fields(self, "work_date")
        if tenant:
            self.fields["employee"].queryset = Employee.objects.filter(tenant=tenant)
            self.fields["shift"].queryset = Shift.objects.filter(tenant=tenant, is_active=True)


class ShiftRotationTemplateForm(forms.ModelForm):
    class Meta:
        model = ShiftRotationTemplate
        fields = ["plant", "name", "cycle_weeks", "pattern", "is_active"]
        widgets = {"pattern": forms.Textarea(attrs={"class": HRIS_TEXTAREA_CLASS, "rows": 4})}

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        _base_init(self, tenant, user)
        self.fields["pattern"].help_text = "Format JSON array, contoh: [\"PAGI\",\"SORE\",\"LIBUR\"]"


class AttendanceCodeForm(forms.ModelForm):
    class Meta:
        model = AttendanceCode
        fields = ["code", "label", "payroll_impact", "is_active"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)


class OvertimeTypeForm(forms.ModelForm):
    class Meta:
        model = OvertimeType
        fields = [
            "code",
            "name",
            "day_category",
            "hour_from",
            "hour_to",
            "multiplier",
            "is_active",
        ]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        self.fields["hour_to"].help_text = "Kosongkan jika berlaku tanpa batas atas (mis. jam II+)."


class AttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = [
            "employee",
            "plant",
            "shift_assignment",
            "work_date",
            "check_in",
            "check_out",
            "source",
            "attendance_code",
            "notes",
        ]
        widgets = {
            "check_in": forms.DateTimeInput(attrs={"type": "datetime-local", "class": HRIS_INPUT_CLASS}),
            "check_out": forms.DateTimeInput(attrs={"type": "datetime-local", "class": HRIS_INPUT_CLASS}),
        }

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        apply_date_fields(self, "work_date")
        _base_init(self, tenant, user)
        if tenant:
            self.fields["employee"].queryset = Employee.objects.filter(tenant=tenant)
            self.fields["shift_assignment"].queryset = ShiftAssignment.objects.filter(tenant=tenant)
            self.fields["attendance_code"].queryset = AttendanceCode.objects.filter(tenant=tenant)


class DailyTimesheetForm(forms.ModelForm):
    class Meta:
        model = DailyTimesheet
        fields = [
            "employee",
            "plant",
            "work_date",
            "shift",
            "shift_code",
            "shift_label",
            "attendance_code",
            "time_off_code",
            "calculation_status",
            "late_in_minutes",
            "early_out_minutes",
            "paid_working_hours",
            "ot_after_minutes",
        ]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        apply_date_fields(self, "work_date")
        _base_init(self, tenant, user)
        if tenant:
            self.fields["employee"].queryset = Employee.objects.filter(tenant=tenant)
            self.fields["shift"].queryset = Shift.objects.filter(tenant=tenant)
            self.fields["attendance_code"].queryset = AttendanceCode.objects.filter(tenant=tenant)


class LeaveTypeForm(forms.ModelForm):
    class Meta:
        model = LeaveType
        fields = [
            "code",
            "name",
            "is_paid",
            "default_quota_days",
            "requires_attachment",
            "is_active",
        ]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)


class LeaveBalanceForm(forms.ModelForm):
    class Meta:
        model = LeaveBalance
        fields = [
            "employee",
            "leave_type",
            "year",
            "opening_balance",
            "accrued",
            "used",
            "pending",
            "remaining",
        ]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        if tenant:
            self.fields["employee"].queryset = Employee.objects.filter(tenant=tenant)
            self.fields["leave_type"].queryset = LeaveType.objects.filter(tenant=tenant)


class AdminLeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = [
            "employee",
            "leave_type",
            "start_date",
            "end_date",
            "days",
            "is_half_day",
            "reason",
            "attachment",
            "status",
            "rejection_reason",
        ]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        apply_date_fields(self, "start_date", "end_date")
        if tenant:
            self.fields["employee"].queryset = Employee.objects.filter(tenant=tenant)
            self.fields["leave_type"].queryset = LeaveType.objects.filter(tenant=tenant)


class LeaveHourlySegmentForm(forms.ModelForm):
    class Meta:
        model = LeaveHourlySegment
        fields = ["leave_request", "start_time", "end_time", "hours"]
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time", "class": HRIS_INPUT_CLASS}),
            "end_time": forms.TimeInput(attrs={"type": "time", "class": HRIS_INPUT_CLASS}),
        }

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        if tenant:
            self.fields["leave_request"].queryset = LeaveRequest.objects.filter(tenant=tenant)


class SalaryComponentForm(forms.ModelForm):
    class Meta:
        model = SalaryComponent
        fields = ["code", "name", "component_type", "formula_key", "is_active"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)


class AdminPayrollRunForm(forms.ModelForm):
    class Meta:
        model = PayrollRun
        fields = ["plant", "period_start", "period_end", "status", "notes"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        apply_date_fields(self, "period_start", "period_end")
        _base_init(self, tenant, user)


class PayslipForm(forms.ModelForm):
    class Meta:
        model = Payslip
        fields = [
            "payroll_run",
            "employee",
            "gross_amount",
            "deduction_amount",
            "net_amount",
            "earnings_breakdown",
            "deductions_breakdown",
        ]
        widgets = {
            "earnings_breakdown": forms.Textarea(attrs={"class": HRIS_TEXTAREA_CLASS, "rows": 3}),
            "deductions_breakdown": forms.Textarea(attrs={"class": HRIS_TEXTAREA_CLASS, "rows": 3}),
        }

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        if tenant:
            self.fields["payroll_run"].queryset = PayrollRun.objects.filter(tenant=tenant)
            self.fields["employee"].queryset = Employee.objects.filter(tenant=tenant)


class THRRunForm(forms.ModelForm):
    class Meta:
        model = THRRun
        fields = ["plant", "year", "status", "notes"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        _base_init(self, tenant, user)


class NotificationAdminForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ["user", "category", "title", "message", "link", "is_read"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        if tenant:
            self.fields["user"].queryset = User.objects.filter(tenant=tenant, is_active=True)
