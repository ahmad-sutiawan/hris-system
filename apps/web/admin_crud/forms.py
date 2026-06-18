from django import forms
from django.contrib.auth import get_user_model

from apps.attendance.models import AttendanceCode, AttendanceRecord, DailyTimesheet, OvertimeType
from apps.core.models import Announcement, FeatureFlag, Notification, Plant, Tenant
from apps.employees.models import Employee, EmployeeDocument
from apps.leave.models import LeaveBalance, LeaveHourlySegment, LeaveRequest, LeaveType
from apps.organization.models import Department, JobPosition
from apps.payroll.models import (
    PayrollRun,
    Payslip,
    Pph21TerBracket,
    Pph21TerCategory,
    Pph21TerPtkpMapping,
    SalaryComponent,
    THRRun,
)
from apps.shifts.models import Shift, ShiftAssignment
from apps.web.forms import (
    HRIS_INPUT_CLASS,
    HRIS_SELECT_CLASS,
    HRIS_TEXTAREA_CLASS,
    _configure_employee_department_shift_fields,
    _filter_plant_queryset,
    _style_fields,
)
from apps.web.widgets import apply_date_fields, apply_time_fields
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
        fields = ["tenant", "code", "name", "is_active"]
        labels = {"name": "Plant name"}

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _base_init(self, tenant, user)
        if tenant:
            self.fields["tenant"].queryset = Tenant.objects.filter(pk=tenant.pk)

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.entity_type = Plant.EntityType.PT
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class BranchForm(forms.ModelForm):
    class Meta:
        model = Plant
        fields = [
            "tenant",
            "parent",
            "code",
            "name",
            "branch_type",
            "timezone",
            "address",
            "latitude",
            "longitude",
            "geo_fence_radius_m",
            "default_shift",
            "is_active",
        ]
        labels = {
            "parent": "Plant",
            "name": "Branch name",
            "branch_type": "Branch type",
        }

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _base_init(self, tenant, user)
        if tenant:
            self.fields["tenant"].queryset = Tenant.objects.filter(pk=tenant.pk)
            self.fields["parent"].queryset = Plant.objects.filter(
                tenant=tenant, entity_type=Plant.EntityType.PT, is_active=True
            )
            self.fields["default_shift"].queryset = Shift.objects.filter(
                tenant=tenant, is_active=True
            )
            self.fields["default_shift"].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.entity_type = Plant.EntityType.BRANCH
        if commit:
            instance.save()
            self.save_m2m()
        return instance


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


from apps.organization.services.codes import department_code_from_name


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["plant", "name", "is_active"]
        labels = {
            "name": "Organization",
            "plant": "Branch Name",
            "is_active": "Aktif",
        }

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        _base_init(self, tenant, user)

    def save(self, commit=True):
        instance = super().save(commit=False)
        tenant_id = instance.tenant_id or (self.tenant.pk if self.tenant else None)
        if not instance.code and instance.name and tenant_id and instance.plant_id:
            instance.code = department_code_from_name(
                instance.name,
                tenant_id=tenant_id,
                plant_id=instance.plant_id,
                exclude_pk=instance.pk,
            )
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class JobPositionForm(forms.ModelForm):
    class Meta:
        model = JobPosition
        fields = ["plant", "department", "code", "title", "is_active"]
        labels = {
            "title": "Job Position",
            "department": "Organization",
            "plant": "Branch Name",
        }

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _base_init(self, tenant, user)
        if tenant:
            self.fields["department"].queryset = Department.objects.filter(tenant=tenant)
            self.fields["department"].label = "Organization"
            self.fields["department"].label_from_instance = lambda obj: obj.name


class Pph21TerCategoryForm(forms.ModelForm):
    class Meta:
        model = Pph21TerCategory
        fields = ["code", "name", "description", "is_active"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _base_init(self, tenant, user)


class Pph21TerPtkpMappingForm(forms.ModelForm):
    class Meta:
        model = Pph21TerPtkpMapping
        fields = ["category", "ptkp_code"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _base_init(self, tenant, user)
        if tenant:
            self.fields["category"].queryset = Pph21TerCategory.objects.filter(tenant=tenant)


class Pph21TerBracketForm(forms.ModelForm):
    class Meta:
        model = Pph21TerBracket
        fields = ["category", "bracket_no", "income_from", "income_to", "rate"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _base_init(self, tenant, user)
        if tenant:
            self.fields["category"].queryset = Pph21TerCategory.objects.filter(tenant=tenant)


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
            "department",
            "job_position",
            "default_shift",
            "manager",
            "user",
            "join_date",
            "contract_end_date",
            "resign_date",
            "status_employee",
            "status",
            "salary_scheme",
            "base_salary",
            "allowance_transport",
            "allowance_meal",
            "allowance_position",
            "tax_status",
            "npwp",
            "pph21_deduct",
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
            from apps.organization.models import JobPosition

            plant_id = self.data.get("plant") or (
                self.instance.plant_id if self.instance.pk else None
            )
            _configure_employee_department_shift_fields(
                self, tenant=tenant, user=user, plant_id=plant_id
            )
            self.fields["job_position"].queryset = JobPosition.objects.filter(tenant=tenant)
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
            "schedule_working_hours": forms.NumberInput(
                attrs={"class": HRIS_INPUT_CLASS, "step": "0.01", "min": "0"}
            ),
        }
        labels = {
            "break_minutes": "Break minutes",
            "grace_period_minutes": "Grace period (minutes)",
            "schedule_working_hours": "Scheduled working hours",
            "cross_day": "Cross-day shift (night)",
            "shift_allowance_code": "Shift allowance code",
            "scheduled_check_in": "Scheduled check-in",
            "scheduled_check_out": "Scheduled check-out",
        }
        help_texts = {
            "break_minutes": "Unpaid break deducted from actual hours (e.g. 60 = 1 hour lunch).",
            "grace_period_minutes": "Tolerance before late-in / early-out penalties apply.",
            "schedule_working_hours": "Paid hours cap per shift; leave blank to auto-calculate from schedule.",
            "cross_day": "Auto-enabled when check-out time is earlier than check-in (night shift).",
            "shift_allowance_code": "Code for shift allowance payroll component (e.g. MALAM, PAGI).",
        }

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        apply_time_fields(self, "scheduled_check_in", "scheduled_check_out")


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
        apply_time_fields(self, "scheduled_check_in", "scheduled_check_out")
        if tenant:
            self.fields["employee"].queryset = Employee.objects.filter(tenant=tenant)
            self.fields["shift"].queryset = Shift.objects.filter(tenant=tenant, is_active=True)


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
        if tenant and "plant" in self.fields:
            self.fields["plant"].queryset = Plant.objects.filter(
                tenant=tenant, entity_type=Plant.EntityType.PT, is_active=True
            )
            self.fields["plant"].label = "Plant"


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


class AnnouncementForm(forms.ModelForm):
    target_roles = forms.MultipleChoiceField(
        choices=User.Role.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Target role",
        help_text="Kosongkan untuk semua role.",
    )
    tags_input = forms.CharField(
        required=False,
        label="Tags",
        help_text="Pisahkan dengan koma, mis. payroll, cuti, libur.",
        widget=forms.TextInput(attrs={"class": HRIS_INPUT_CLASS}),
    )

    class Meta:
        model = Announcement
        fields = [
            "title",
            "summary",
            "body",
            "category",
            "priority",
            "plant",
            "publish_start",
            "publish_end",
            "is_active",
            "is_pinned",
            "require_acknowledgment",
            "attachment",
            "external_link",
            "action_label",
        ]
        labels = {
            "title": "Judul",
            "summary": "Ringkasan",
            "body": "Konten lengkap",
            "category": "Kategori",
            "priority": "Prioritas",
            "plant": "Plant target",
            "publish_start": "Terbit mulai",
            "publish_end": "Terbit sampai",
            "is_active": "Aktif",
            "is_pinned": "Sematkan di atas",
            "require_acknowledgment": "Wajib diakui pengguna",
            "attachment": "Lampiran",
            "external_link": "Tautan eksternal",
            "action_label": "Label tombol tautan",
        }
        widgets = {
            "summary": forms.Textarea(attrs={"class": HRIS_TEXTAREA_CLASS, "rows": 3}),
            "body": forms.Textarea(attrs={"class": HRIS_TEXTAREA_CLASS, "rows": 14}),
            "external_link": forms.URLInput(attrs={"class": HRIS_INPUT_CLASS}),
            "action_label": forms.TextInput(attrs={"class": HRIS_INPUT_CLASS}),
        }

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        _base_init(self, tenant, user)
        if tenant and "plant" in self.fields:
            self.fields["plant"].required = False
            self.fields["plant"].empty_label = "Semua plant"
        for field_name in ("publish_start", "publish_end"):
            if field_name not in self.fields:
                continue
            self.fields[field_name].widget = forms.DateTimeInput(
                attrs={"class": HRIS_INPUT_CLASS, "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            )
            self.fields[field_name].input_formats = [
                "%Y-%m-%dT%H:%M",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
            ]
        if self.instance.pk:
            if self.instance.target_roles:
                self.initial["target_roles"] = self.instance.target_roles
            if self.instance.tags:
                self.initial["tags_input"] = ", ".join(self.instance.tags)
        elif "publish_start" in self.fields:
            from django.utils import timezone

            self.initial.setdefault("publish_start", timezone.localtime())

        if commit:
            instance.save()
            self.save_m2m()
        return instance


class TalentaMasterForm(forms.ModelForm):
    class Meta:
        from apps.employees.models import TalentaMaster

        model = TalentaMaster
        fields = ["category", "code", "name", "is_active"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _base_init(self, tenant, user)


class JobLevelForm(forms.ModelForm):
    class Meta:
        from apps.organization.models import JobLevel

        model = JobLevel
        fields = ["code", "name", "rank", "is_active"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _base_init(self, tenant, user)


class PunchLocationForm(forms.ModelForm):
    class Meta:
        from apps.core.models import PunchLocation

        model = PunchLocation
        fields = ["plant", "name", "latitude", "longitude", "radius_m", "is_active"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _base_init(self, tenant, user)


class HolidayCalendarForm(forms.ModelForm):
    class Meta:
        from apps.core.models import HolidayCalendar

        model = HolidayCalendar
        fields = ["name", "holiday_date", "holiday_type", "plant", "is_active"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _base_init(self, tenant, user)
        apply_date_fields(self, "holiday_date")


class ApprovalLineForm(forms.ModelForm):
    class Meta:
        from apps.core.models import ApprovalLine

        model = ApprovalLine
        fields = ["request_type", "step_order", "approver_kind", "is_active"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _base_init(self, tenant, user)


class ShiftAllowanceRateForm(forms.ModelForm):
    class Meta:
        from apps.payroll.models import ShiftAllowanceRate

        model = ShiftAllowanceRate
        fields = ["code", "name", "amount", "is_active"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _base_init(self, tenant, user)
