from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone

from apps.attendance.models import OvertimeRequest, OvertimeType
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
        labels = {
            "employee_id": "ID Karyawan",
            "full_name": "Nama lengkap",
            "legal_entity": "Legal entity",
            "join_date": "Tanggal bergabung",
            "contract_end_date": "Akhir kontrak",
            "resign_date": "Tanggal resign",
            "employee_grade": "Grade karyawan",
            "salary_scheme": "Skema gaji",
            "base_salary": "Gaji pokok",
            "allowance_transport": "Tunjangan transport",
            "allowance_meal": "Tunjangan makan",
            "allowance_position": "Tunjangan jabatan",
            "tax_status": "Status PPh21",
            "npwp": "NPWP",
            "bpjs_kesehatan_number": "No. BPJS Kesehatan",
            "bpjs_ketenagakerjaan_number": "No. BPJS Ketenagakerjaan",
            "user": "Akun login",
        }

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        apply_date_fields(self, "join_date", "contract_end_date", "resign_date")
        self.fields["user"].required = False
        self.fields["legal_entity"].required = False
        self.fields["user"].help_text = (
            "Hubungkan ke akun login agar karyawan bisa clock in, ajukan cuti, dan lihat slip gaji."
        )
        if tenant:
            from apps.organization.models import Department, EmployeeGrade, JobPosition, LegalEntity

            _filter_plant_queryset(self, tenant, user)
            self.fields["legal_entity"].queryset = LegalEntity.objects.filter(
                tenant=tenant, is_active=True
            )

            plant_id = self._resolve_plant_id(user)
            dept_qs = Department.objects.filter(tenant=tenant, is_active=True)
            job_qs = JobPosition.objects.filter(tenant=tenant, is_active=True)
            grade_qs = EmployeeGrade.objects.filter(tenant=tenant, is_active=True)
            if plant_id:
                dept_qs = dept_qs.filter(plant_id=plant_id)
                job_qs = job_qs.filter(plant_id=plant_id)
                grade_qs = grade_qs.filter(plant_id=plant_id)
            self.fields["department"].queryset = dept_qs
            self.fields["job_position"].queryset = job_qs
            self.fields["employee_grade"].queryset = grade_qs
            self.fields["employee_grade"].required = False
            self.fields["employee_grade"].help_text = (
                "Golongan menentukan gaji harian dasar perhitungan gaji pokok dan lembur."
            )
            self.fields["salary_scheme"].help_text = (
                "Daily: gaji pokok = gaji harian grade × hari hadir. Monthly: gaji pokok tetap bulanan."
            )
            self.fields["manager"].queryset = Employee.objects.filter(tenant=tenant).exclude(
                status__in=[Employee.Status.INACTIVE, Employee.Status.RESIGNED]
            )
            current_user_id = self.instance.user_id if self.instance.pk else None
            self.fields["user"].queryset = available_users_for_employee(tenant, current_user_id)
            if self.instance.pk:
                self.fields["manager"].queryset = self.fields["manager"].queryset.exclude(
                    pk=self.instance.pk
                )

    def _resolve_plant_id(self, user):
        if self.data.get("plant"):
            return self.data.get("plant")
        if self.instance.pk and self.instance.plant_id:
            return self.instance.plant_id
        if user and user.plant_id and not user.is_admin:
            return user.plant_id
        return None

    def clean(self):
        cleaned = super().clean()
        plant = cleaned.get("plant")
        department = cleaned.get("department")
        job_position = cleaned.get("job_position")
        if department and plant and department.plant_id != plant.pk:
            self.add_error("department", "Department harus sesuai plant yang dipilih.")
        if job_position and plant and job_position.plant_id != plant.pk:
            self.add_error("job_position", "Jabatan harus sesuai plant yang dipilih.")
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
        fields = [
            "employee",
            "shift",
            "work_date",
            "scheduled_check_in",
            "scheduled_check_out",
        ]
        labels = {
            "work_date": "Tanggal kerja",
            "scheduled_check_in": "Jam masuk (override)",
            "scheduled_check_out": "Jam pulang (override)",
        }
        widgets = {
            "scheduled_check_in": forms.TimeInput(attrs={"type": "time", "class": HRIS_INPUT_CLASS}),
            "scheduled_check_out": forms.TimeInput(attrs={"type": "time", "class": HRIS_INPUT_CLASS}),
        }

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        apply_date_fields(self, "work_date")
        self.fields["scheduled_check_in"].required = False
        self.fields["scheduled_check_out"].required = False
        self.fields["scheduled_check_in"].help_text = (
            "Kosongkan untuk pakai jam dari master shift. Isi manual untuk long shift / perubahan dadakan."
        )
        self.fields["scheduled_check_out"].help_text = (
            "Bisa melewati tengah malam (contoh masuk 22:00, pulang 06:00)."
        )
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

    def clean(self):
        cleaned = super().clean()
        shift = cleaned.get("shift")
        sched_in = cleaned.get("scheduled_check_in") or (shift.scheduled_check_in if shift else None)
        sched_out = cleaned.get("scheduled_check_out") or (shift.scheduled_check_out if shift else None)
        if shift and sched_in and sched_out:
            if not shift.cross_day and sched_out <= sched_in:
                self.add_error(
                    "scheduled_check_out",
                    "Jam pulang harus setelah jam masuk, atau aktifkan cross-day di master shift.",
                )
        cleaned["scheduled_check_in"] = sched_in
        cleaned["scheduled_check_out"] = sched_out
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.scheduled_check_in and instance.shift_id:
            instance.scheduled_check_in = instance.shift.scheduled_check_in
        if not instance.scheduled_check_out and instance.shift_id:
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


class OvertimeRequestForm(forms.ModelForm):
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.none(),
        required=False,
        label="Karyawan",
        help_text="Pilih karyawan yang mengajukan lembur.",
    )

    class Meta:
        model = OvertimeRequest
        fields = ["overtime_type", "work_date", "ot_before_minutes", "ot_after_minutes", "reason"]
        labels = {
            "overtime_type": "Jenis lembur",
            "work_date": "Tanggal lembur",
            "ot_before_minutes": "Lembur sebelum shift (menit)",
            "ot_after_minutes": "Lembur sesudah shift (menit)",
            "reason": "Alasan / keterangan",
        }

    def __init__(
        self,
        *args,
        tenant=None,
        user=None,
        show_employee_picker=False,
        profile=None,
        suggested_ot=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.profile = profile
        self.show_employee_picker = show_employee_picker
        _style_fields(self)
        apply_date_fields(self, "work_date")
        self.fields["ot_before_minutes"].widget.attrs.setdefault("min", "0")
        self.fields["ot_after_minutes"].widget.attrs.setdefault("min", "0")

        if suggested_ot and not self.is_bound:
            before, after = suggested_ot
            if before:
                self.fields["ot_before_minutes"].initial = before
            if after:
                self.fields["ot_after_minutes"].initial = after

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
        else:
            del self.fields["employee"]

        if tenant:
            self.fields["overtime_type"].queryset = OvertimeType.objects.filter(
                tenant=tenant, is_active=True
            )
            self.fields["overtime_type"].empty_label = "— Pilih jenis lembur —"

    def clean(self):
        cleaned = super().clean()
        before = cleaned.get("ot_before_minutes") or 0
        after = cleaned.get("ot_after_minutes") or 0
        if before <= 0 and after <= 0:
            self.add_error(
                "ot_after_minutes",
                "Isi durasi lembur sebelum atau sesudah shift (minimal satu > 0).",
            )

        if self.show_employee_picker:
            employee = cleaned.get("employee") or self.profile
            if not employee:
                self.add_error("employee", "Pilih karyawan yang mengajukan lembur.")
            else:
                cleaned["employee"] = employee
        elif self.profile:
            cleaned["employee"] = self.profile

        return cleaned


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
