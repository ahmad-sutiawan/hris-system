from django import forms

from apps.core.models import Plant
from apps.employees.models import Employee
from apps.leave.models import LeaveRequest, LeaveType
from apps.payroll.models import PayrollRun
from apps.shifts.models import Shift, ShiftAssignment


HRIS_INPUT_CLASS = "hris-input"
HRIS_SELECT_CLASS = "hris-select"
HRIS_TEXTAREA_CLASS = "hris-textarea"


def _style_fields(form):
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
            continue
        if isinstance(widget, forms.Select):
            widget.attrs.setdefault("class", HRIS_SELECT_CLASS)
        elif isinstance(widget, forms.Textarea):
            widget.attrs.setdefault("class", HRIS_TEXTAREA_CLASS)
        elif isinstance(widget, forms.DateInput):
            widget.input_type = "date"
            widget.attrs.setdefault("class", HRIS_INPUT_CLASS)
        else:
            widget.attrs.setdefault("class", HRIS_INPUT_CLASS)


def _filter_plant_queryset(form, tenant, user=None):
    if tenant and "plant" in form.fields:
        qs = Plant.objects.filter(tenant=tenant)
        if user and user.plant_id and not user.is_admin:
            qs = qs.filter(pk=user.plant_id)
        form.fields["plant"].queryset = qs


class EmployeeForm(forms.ModelForm):
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
            "manager",
            "join_date",
            "status",
            "base_salary",
            "allowance_transport",
            "tax_status",
            "bank_name",
            "bank_account_number",
            "bank_account_name",
        ]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        if tenant:
            from apps.organization.models import Department, JobPosition

            _filter_plant_queryset(self, tenant, user)
            self.fields["department"].queryset = Department.objects.filter(tenant=tenant)
            self.fields["job_position"].queryset = JobPosition.objects.filter(tenant=tenant)
            self.fields["manager"].queryset = Employee.objects.filter(tenant=tenant).exclude(
                status__in=[Employee.Status.INACTIVE, Employee.Status.RESIGNED]
            )
            if self.instance.pk:
                self.fields["manager"].queryset = self.fields["manager"].queryset.exclude(
                    pk=self.instance.pk
                )


class ShiftAssignmentForm(forms.ModelForm):
    class Meta:
        model = ShiftAssignment
        fields = ["employee", "shift", "work_date"]

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        if tenant:
            emp_qs = Employee.objects.filter(tenant=tenant).exclude(
                status__in=[Employee.Status.INACTIVE, Employee.Status.RESIGNED]
            )
            shift_qs = Shift.objects.filter(tenant=tenant, is_active=True)
            if user and user.plant_id and not user.is_admin:
                emp_qs = emp_qs.filter(plant=user.plant)
                shift_qs = shift_qs.filter(plant=user.plant)
            self.fields["employee"].queryset = emp_qs
            self.fields["shift"].queryset = shift_qs

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.scheduled_check_in = instance.shift.scheduled_check_in
        instance.scheduled_check_out = instance.shift.scheduled_check_out
        if commit:
            instance.save()
        return instance


class LeaveRequestForm(forms.ModelForm):
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.none(),
        required=False,
        label="Karyawan",
        help_text="Wajib diisi jika Anda mengajukan cuti atas nama karyawan.",
    )

    class Meta:
        model = LeaveRequest
        fields = ["leave_type", "start_date", "end_date", "is_half_day", "reason"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, tenant=None, user=None, show_employee=False, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        if show_employee:
            emp_qs = Employee.objects.filter(tenant=tenant).exclude(
                status__in=[Employee.Status.INACTIVE, Employee.Status.RESIGNED]
            )
            if user and user.plant_id and not user.is_admin:
                emp_qs = emp_qs.filter(plant=user.plant)
            self.fields["employee"].queryset = emp_qs
        else:
            del self.fields["employee"]

        if tenant:
            self.fields["leave_type"].queryset = LeaveType.objects.filter(
                tenant=tenant, is_active=True
            )

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            raise forms.ValidationError("Tanggal selesai harus >= tanggal mulai.")
        return cleaned


class PayrollRunForm(forms.ModelForm):
    class Meta:
        model = PayrollRun
        fields = ["plant", "period_start", "period_end", "notes"]
        widgets = {
            "period_start": forms.DateInput(attrs={"type": "date"}),
            "period_end": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        if tenant:
            _filter_plant_queryset(self, tenant, user)

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("period_start")
        end = cleaned.get("period_end")
        if start and end and end < start:
            raise forms.ValidationError("Tanggal akhir periode harus >= tanggal mulai.")
        return cleaned
