from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone

from apps.attendance.models import OvertimeRequest, OvertimeType
from apps.attendance.models import AttendanceCode, DailyTimesheet
from apps.core.models import Plant
from apps.employees.models import Employee, EmployeeDocument
from apps.leave.models import LeaveRequest, LeaveType
from apps.payroll.models import PayrollRun
from apps.shifts.models import Shift, ShiftAssignment


from apps.employees.talenta_vocabulary import STATUS_EMPLOYEE_VALUES
from apps.web.widgets import apply_date_fields, apply_time_fields


HRIS_INPUT_CLASS = "hris-input"
HRIS_SELECT_CLASS = "hris-select"
HRIS_TEXTAREA_CLASS = "hris-textarea"

PTKP_CHOICES = [
    ("N/A", "N/A — belum diisi"),
    ("", "— Tidak diisi —"),
    ("TK/0", "TK/0 — Tidak kawin, 0 tanggungan"),
    ("TK/1", "TK/1 — Tidak kawin, 1 tanggungan"),
    ("TK/2", "TK/2 — Tidak kawin, 2 tanggungan"),
    ("TK/3", "TK/3 — Tidak kawin, 3 tanggungan"),
    ("K/0", "K/0 — Kawin, 0 tanggungan"),
    ("K/1", "K/1 — Kawin, 1 tanggungan"),
    ("K/2", "K/2 — Kawin, 2 tanggungan"),
    ("K/3", "K/3 — Kawin, 3 tanggungan"),
]


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


def _configure_employee_department_shift_fields(form, *, tenant, user, plant_id=None):
    from apps.organization.models import Department, JobLevel, JobPosition

    plant_id = plant_id or (
        form.data.get("plant")
        if form.data
        else (form.instance.plant_id if form.instance.pk else None)
    )
    if user and user.plant_id and not user.is_admin and not plant_id:
        plant_id = user.plant_id

    dept_qs = Department.objects.filter(tenant=tenant, is_active=True)
    job_qs = JobPosition.objects.filter(tenant=tenant, is_active=True)
    level_qs = JobLevel.objects.filter(tenant=tenant, is_active=True)
    shift_qs = Shift.objects.filter(tenant=tenant, is_active=True)
    if plant_id:
        dept_qs = dept_qs.filter(plant_id=plant_id)
        job_qs = job_qs.filter(plant_id=plant_id)
        shift_qs = shift_qs.filter(plant_id=plant_id)

    form.fields["department"].queryset = dept_qs
    form.fields["department"].label = "Organization"
    form.fields["department"].label_from_instance = lambda obj: obj.name
    form.fields["job_position"].queryset = job_qs
    form.fields["job_position"].label = "Job Position"
    if "job_level" in form.fields:
        form.fields["job_level"].queryset = level_qs
        form.fields["job_level"].required = False
        form.fields["job_level"].empty_label = "— Pilih Job Level —"
        form.fields["job_level"].label = "Job Level"
    form.fields["default_shift"].queryset = shift_qs
    form.fields["default_shift"].required = False
    form.fields["default_shift"].empty_label = "— Pilih shift —"
    form.fields["default_shift"].label = "Shift default"
    form.fields["default_shift"].help_text = (
        "Shift tetap untuk karyawan ini. Penjadwalan hari ini diperbarui otomatis saat disimpan."
    )


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
            "photo",
            "nik",
            "email",
            "phone",
            "address",
            "mother_name",
            "birth_place",
            "birth_date",
            "gender",
            "marital_status",
            "plant",
            "department",
            "job_position",
            "job_level",
            "default_shift",
            "manager",
            "join_date",
            "contract_end_date",
            "resign_date",
            "status_employee",
            "status",
        ]
        labels = {
            "employee_id": "Employee ID",
            "full_name": "Full Name",
            "photo": "Profile Picture",
            "nik": "NIK (NPWP 16 Digit)",
            "email": "Email",
            "phone": "Mobile Phone",
            "address": "Residential Address",
            "mother_name": "Nama ibu kandung",
            "birth_place": "Birth Place",
            "birth_date": "Birth Date",
            "gender": "Gender",
            "marital_status": "Marital Status",
            "plant": "Branch Name",
            "department": "Organization",
            "job_position": "Job Position",
            "join_date": "Join Date",
            "contract_end_date": "End Date",
            "resign_date": "Resign Date",
            "status_employee": "Status Employee",
            "default_shift": "Shift default",
            "job_level": "Job Level",
        }

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        apply_date_fields(self, "join_date", "contract_end_date", "resign_date", "birth_date")
        if "status_employee" in self.fields:
            self.fields["status_employee"].required = False
            self.fields["status_employee"].widget = forms.Select(
                choices=[("", "— Pilih Status Employee —")]
                + [(value, value) for value in STATUS_EMPLOYEE_VALUES]
            )
        self.fields["photo"].required = False
        self.fields["address"].widget = forms.Textarea(attrs={"rows": 3, "class": HRIS_TEXTAREA_CLASS})
        for name in (
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
            "gender",
            "marital_status",
            "birth_place",
            "birth_date",
        ):
            if name in self.fields:
                self.fields[name].required = True
        if tenant:
            _filter_plant_queryset(self, tenant, user)
            plant_id = self._resolve_plant_id(user)
            _configure_employee_department_shift_fields(
                self, tenant=tenant, user=user, plant_id=plant_id
            )
            self.fields["manager"].queryset = Employee.objects.filter(tenant=tenant).exclude(
                status__in=[Employee.Status.INACTIVE, Employee.Status.RESIGNED]
            )
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
        default_shift = cleaned.get("default_shift")
        if department and plant and department.plant_id != plant.pk:
            self.add_error("department", "Department harus sesuai plant yang dipilih.")
        if job_position and plant and job_position.plant_id != plant.pk:
            self.add_error("job_position", "Jabatan harus sesuai plant yang dipilih.")
        if default_shift and plant and default_shift.plant_id != plant.pk:
            self.add_error("default_shift", "Shift harus sesuai plant yang dipilih.")
        return cleaned


class EmployeeCompensationForm(forms.ModelForm):
    tax_status = forms.ChoiceField(
        choices=PTKP_CHOICES,
        required=True,
        label="Status PTKP (PPh 21)",
    )
    pph21_deduct = forms.ChoiceField(
        choices=[("", "Otomatis"), ("1", "Ya"), ("0", "Tidak")],
        required=False,
        label="Potong PPh 21",
    )

    class Meta:
        model = Employee
        fields = [
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
        labels = {
            "salary_scheme": "Skema gaji",
            "base_salary": "Gaji pokok",
            "allowance_transport": "Tunjangan transport",
            "allowance_meal": "Tunjangan makan",
            "allowance_position": "Tunjangan jabatan",
            "npwp": "NPWP",
            "bpjs_kesehatan_number": "No. BPJS Kesehatan",
            "bpjs_ketenagakerjaan_number": "No. BPJS Ketenagakerjaan",
        }

    def __init__(self, *args, tenant=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        _style_fields(self)
        self.fields["salary_scheme"].help_text = (
            "Daily: gaji pokok × hari hadir + tunjangan harian. "
            "Monthly: gaji pokok + tunjangan tetap bulanan."
        )
        self.fields["tax_status"].help_text = (
            "Status PTKP menentukan kategori TER (A/B/C) sesuai PP No. 58 Tahun 2023."
        )
        self.fields["pph21_deduct"].help_text = (
            "Kosong = otomatis potong jika PTKP diisi. Pilih Tidak untuk mengecualikan."
        )
        if self.instance.pk:
            if self.instance.pph21_deduct is True:
                self.fields["pph21_deduct"].initial = "1"
            elif self.instance.pph21_deduct is False:
                self.fields["pph21_deduct"].initial = "0"

    def clean_pph21_deduct(self):
        raw = self.cleaned_data.get("pph21_deduct")
        if raw in (None, ""):
            return None
        return raw == "1"

    def clean_tax_status(self):
        value = self.cleaned_data.get("tax_status") or ""
        if not value:
            raise forms.ValidationError("Status PTKP wajib diisi.")
        if value == "N/A":
            return value
        return value


class EmployeeDocumentUploadForm(forms.Form):
    ktp_file = forms.FileField(
        label="Upload KTP",
        required=False,
        help_text="Maksimal 1 MB. Format PDF/JPG/PNG.",
    )
    kk_file = forms.FileField(
        label="Upload KK",
        required=False,
        help_text="Maksimal 1 MB. Format PDF/JPG/PNG.",
    )

    def _validate_file(self, field_name):
        upload = self.cleaned_data.get(field_name)
        if upload and upload.size > 1024 * 1024:
            raise forms.ValidationError("Ukuran file maksimal 1 MB.")
        return upload

    def clean_ktp_file(self):
        return self._validate_file("ktp_file")

    def clean_kk_file(self):
        return self._validate_file("kk_file")


class AttendanceCorrectionForm(forms.Form):
    check_in_time = forms.TimeField(
        label="Jam masuk",
        required=False,
        widget=forms.TimeInput(attrs={"type": "time", "class": HRIS_INPUT_CLASS}),
    )
    check_out_time = forms.TimeField(
        label="Jam pulang",
        required=False,
        widget=forms.TimeInput(attrs={"type": "time", "class": HRIS_INPUT_CLASS}),
    )
    shift = forms.ModelChoiceField(
        queryset=Shift.objects.none(),
        required=False,
        label="Shift",
        empty_label="— Tanpa perubahan —",
    )
    scheduled_check_in = forms.TimeField(
        label="Schedule in",
        required=False,
        widget=forms.TimeInput(attrs={"type": "time", "class": HRIS_INPUT_CLASS}),
    )
    scheduled_check_out = forms.TimeField(
        label="Schedule out",
        required=False,
        widget=forms.TimeInput(attrs={"type": "time", "class": HRIS_INPUT_CLASS}),
    )
    attendance_code = forms.ModelChoiceField(
        queryset=AttendanceCode.objects.none(),
        required=False,
        label="Kode absensi",
        empty_label="— Tanpa perubahan —",
    )

    def __init__(self, *args, tenant=None, timesheet=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.timesheet = timesheet
        if tenant and timesheet:
            plant = timesheet.employee.plant
            self.fields["shift"].queryset = Shift.objects.filter(
                tenant=tenant, plant=plant, is_active=True
            )
            self.fields["attendance_code"].queryset = AttendanceCode.objects.filter(
                tenant=tenant, is_active=True
            )
        if timesheet and not self.is_bound:
            if timesheet.check_in:
                self.fields["check_in_time"].initial = timezone.localtime(timesheet.check_in).time()
            if timesheet.check_out:
                self.fields["check_out_time"].initial = timezone.localtime(timesheet.check_out).time()
            if timesheet.scheduled_check_in:
                self.fields["scheduled_check_in"].initial = timesheet.scheduled_check_in
            if timesheet.scheduled_check_out:
                self.fields["scheduled_check_out"].initial = timesheet.scheduled_check_out
            if timesheet.shift_id:
                self.fields["shift"].initial = timesheet.shift_id
            if timesheet.attendance_code_id:
                self.fields["attendance_code"].initial = timesheet.attendance_code_id

    def clean(self):
        cleaned = super().clean()
        has_change = any(
            cleaned.get(field)
            for field in (
                "check_in_time",
                "check_out_time",
                "shift",
                "scheduled_check_in",
                "scheduled_check_out",
                "attendance_code",
            )
        )
        if not has_change:
            raise forms.ValidationError("Isi minimal satu field untuk dikoreksi.")
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
        apply_time_fields(self, "scheduled_check_in", "scheduled_check_out")
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
        fields = [
            "overtime_type",
            "work_date",
            "ot_after_minutes",
            "compensation_mode",
            "reason",
        ]
        labels = {
            "overtime_type": "Jenis lembur",
            "work_date": "Tanggal lembur",
            "ot_after_minutes": "Lembur sesudah shift (menit)",
            "compensation_mode": "Kompensasi lembur",
            "reason": "Alasan / keterangan",
        }
        widgets = {
            "compensation_mode": forms.RadioSelect,
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
        self.fields["ot_after_minutes"].widget.attrs.setdefault("min", "1")
        self.fields["compensation_mode"].help_text = (
            "Diuangkan: masuk slip gaji sesuai gaji harian/pokok dan tarif lembur. "
            "Tambah jatah cuti: 8 jam lembur disetujui = 1 hari cuti (jenis CL)."
        )
        self.fields["compensation_mode"].initial = OvertimeRequest.CompensationMode.CASH
        self.fields["compensation_mode"].required = False

        if suggested_ot and not self.is_bound:
            _before, after = suggested_ot
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
        after = cleaned.get("ot_after_minutes") or 0
        if after <= 0:
            self.add_error(
                "ot_after_minutes",
                "Isi durasi lembur sesudah shift (minimal 1 menit).",
            )
        cleaned["ot_before_minutes"] = 0

        if self.show_employee_picker:
            employee = cleaned.get("employee") or self.profile
            if not employee:
                self.add_error("employee", "Pilih karyawan yang mengajukan lembur.")
            else:
                cleaned["employee"] = employee
        elif self.profile:
            cleaned["employee"] = self.profile

        if not cleaned.get("compensation_mode"):
            cleaned["compensation_mode"] = OvertimeRequest.CompensationMode.CASH

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
