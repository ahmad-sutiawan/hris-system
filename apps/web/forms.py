from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone

from apps.core.models import Plant
from apps.employees.models import Employee
from apps.leave.models import LeaveRequest, LeaveType
from apps.payroll.models import PayrollRun
from apps.shifts.models import Shift, ShiftAssignment


from apps.web.widgets import apply_date_fields
from apps.employees.services.user_link import available_users_for_employee


HRIS_INPUT_CLASS = "hris-input"
HRIS_SELECT_CLASS = "hris-select"
HRIS_TEXTAREA_CLASS = "hris-textarea"


def _style_fields(form):
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
            continue
        if isinstance(widget, forms.DateInput):
            continue
        if isinstance(widget, forms.Select):
            widget.attrs.setdefault("class", HRIS_SELECT_CLASS)
        elif isinstance(widget, forms.Textarea):
            widget.attrs.setdefault("class", HRIS_TEXTAREA_CLASS)
        else:
            widget.attrs.setdefault("class", HRIS_INPUT_CLASS)


def _filter_plant_queryset(form, tenant, user=None):
    if tenant and "plant" in form.fields:
        qs = Plant.objects.filter(tenant=tenant)
        if user and user.plant_id and not user.is_admin:
            qs = qs.filter(pk=user.plant_id)
        form.fields["plant"].queryset = qs


class HRISLoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Username atau password salah. Periksa kembali kredensial Anda.",
        "inactive": "Akun ini nonaktif. Hubungi administrator HRIS.",
    }

    username = forms.CharField(
        label="Username",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": HRIS_INPUT_CLASS,
                "placeholder": "Masukkan username",
                "autocomplete": "username",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": HRIS_INPUT_CLASS,
                "placeholder": "Masukkan password",
                "autocomplete": "current-password",
            }
        ),
    )
    remember_me = forms.BooleanField(
        label="Ingat saya selama 14 hari",
        required=False,
    )


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
            "user",
            "join_date",
            "status",
            "base_salary",
            "allowance_transport",
            "tax_status",
            "bank_name",
            "bank_account_number",
            "bank_account_name",
        ]
        labels = {
            "employee_id": "ID Karyawan",
            "full_name": "Nama lengkap",
            "join_date": "Tanggal bergabung",
            "base_salary": "Gaji pokok",
            "allowance_transport": "Tunjangan transport",
            "tax_status": "Status PPh21",
            "user": "Akun login",
        }

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        apply_date_fields(self, "join_date")
        self.fields["user"].required = False
        self.fields["user"].help_text = (
            "Hubungkan ke akun login agar karyawan bisa clock in, ajukan cuti, dan lihat slip gaji."
        )
        if tenant:
            from apps.organization.models import Department, JobPosition

            _filter_plant_queryset(self, tenant, user)
            self.fields["department"].queryset = Department.objects.filter(tenant=tenant)
            self.fields["job_position"].queryset = JobPosition.objects.filter(tenant=tenant)
            self.fields["manager"].queryset = Employee.objects.filter(tenant=tenant).exclude(
                status__in=[Employee.Status.INACTIVE, Employee.Status.RESIGNED]
            )
            current_user_id = self.instance.user_id if self.instance.pk else None
            self.fields["user"].queryset = available_users_for_employee(tenant, current_user_id)
            if self.instance.pk:
                self.fields["manager"].queryset = self.fields["manager"].queryset.exclude(
                    pk=self.instance.pk
                )

    def clean(self):
        cleaned = super().clean()
        linked_user = cleaned.get("user")
        email = cleaned.get("email")
        if linked_user and email and not linked_user.email:
            linked_user.email = email
            linked_user.save(update_fields=["email"])
        elif linked_user and email and linked_user.email.lower() != email.lower():
            self.add_error(
                "email",
                f"Email harus sama dengan akun login ({linked_user.email}) atau kosongkan salah satu.",
            )
        return cleaned


class ShiftAssignmentForm(forms.ModelForm):
    class Meta:
        model = ShiftAssignment
        fields = ["employee", "shift", "work_date"]
        labels = {
            "work_date": "Tanggal kerja",
        }

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        apply_date_fields(self, "work_date")
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
        help_text="Pilih karyawan yang mengajukan cuti.",
    )

    class Meta:
        model = LeaveRequest
        fields = ["leave_type", "start_date", "end_date", "is_half_day", "reason"]
        labels = {
            "leave_type": "Jenis cuti",
            "start_date": "Tanggal mulai",
            "end_date": "Tanggal selesai",
            "is_half_day": "Setengah hari",
            "reason": "Alasan / keterangan",
        }

    def __init__(
        self,
        *args,
        tenant=None,
        user=None,
        show_employee_picker=False,
        profile=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.profile = profile
        self.show_employee_picker = show_employee_picker
        _style_fields(self)
        apply_date_fields(self, "start_date", "end_date")
        today = timezone.localdate().isoformat()
        self.fields["start_date"].widget.attrs.setdefault("min", today)
        self.fields["end_date"].widget.attrs.setdefault("min", today)

        if show_employee_picker:
            emp_qs = Employee.objects.filter(tenant=tenant).exclude(
                status__in=[Employee.Status.INACTIVE, Employee.Status.RESIGNED]
            )
            if user and user.plant_id and not user.is_admin:
                emp_qs = emp_qs.filter(plant=user.plant)
            self.fields["employee"].queryset = emp_qs
            self.fields["employee"].required = profile is None
            if profile:
                self.fields["employee"].empty_label = f"Diri sendiri — {profile.full_name}"
                self.fields["employee"].help_text = (
                    "Biarkan 'Diri sendiri' untuk mengajukan cuti sendiri, "
                    "atau pilih karyawan lain."
                )
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
        if cleaned.get("is_half_day") and start:
            cleaned["end_date"] = start
            end = start
        if start and end and end < start:
            self.add_error("end_date", "Tanggal selesai harus sama atau setelah tanggal mulai.")

        if self.show_employee_picker:
            employee = cleaned.get("employee") or self.profile
            if not employee:
                self.add_error("employee", "Pilih karyawan yang mengajukan cuti.")
            else:
                cleaned["employee"] = employee
        elif self.profile:
            cleaned["employee"] = self.profile

        return cleaned

    @property
    def resolved_employee(self):
        if not self.is_bound:
            return self.profile
        if not self.is_valid():
            return None
        return self.cleaned_data.get("employee")


class PayrollRunForm(forms.ModelForm):
    class Meta:
        model = PayrollRun
        fields = ["plant", "period_start", "period_end", "notes"]
        labels = {
            "period_start": "Periode mulai",
            "period_end": "Periode akhir",
            "notes": "Catatan",
        }

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        apply_date_fields(self, "period_start", "period_end")
        if tenant:
            _filter_plant_queryset(self, tenant, user)

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("period_start")
        end = cleaned.get("period_end")
        if start and end and end < start:
            raise forms.ValidationError("Tanggal akhir periode harus >= tanggal mulai.")
        return cleaned
