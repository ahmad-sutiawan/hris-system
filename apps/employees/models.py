from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from apps.core.fields import EncryptedCharField, EncryptedDecimalField
from apps.core.models.base import TenantScopedModel


class TalentaMaster(TenantScopedModel):
    """Referensi dinamis dari export Talenta."""

    class Category(models.TextChoices):
        RELIGION = "religion", "Religion"
        BLOOD_TYPE = "blood_type", "Blood Type"
        NATIONALITY = "nationality", "Nationality Code"
        CURRENCY = "currency", "Currency"
        PAYMENT_SCHEDULE = "payment_schedule", "Payment Schedule"
        APPROVAL_LINE = "approval_line", "Approval Line"
        GRADE = "grade", "Grade"
        EMPLOYEE_CLASS = "employee_class", "Class"
        COST_CENTER = "cost_center", "Cost Center"
        COST_CENTER_CATEGORY = "cost_center_category", "Cost Center Category"
        SBU = "sbu", "SBU"
        EMPLOYEE_TAX_STATUS = "employee_tax_status", "Employee Tax Status"
        TAX_CONFIG = "tax_config", "Tax Config"

    category = models.CharField(max_length=32, choices=Category.choices)
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name"]
        unique_together = [["tenant", "category", "name"]]
        indexes = [
            models.Index(fields=["tenant", "category", "is_active"]),
        ]

    def __str__(self):
        return f"{self.get_category_display()}: {self.name}"


class Employee(TenantScopedModel):
    class Status(models.TextChoices):
        PROBATION = "probation", "Probation"
        PERMANENT = "permanent", "Permanent"
        CONTRACT = "contract", "Contract"
        INTERN = "intern", "Intern"
        INACTIVE = "inactive", "Inactive"
        RESIGNED = "resigned", "Resigned"

    class SalaryScheme(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        DAILY = "daily", "Daily"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_profile",
    )
    plant = models.ForeignKey(
        "core.Plant",
        on_delete=models.PROTECT,
        related_name="employees",
    )
    legal_entity = models.ForeignKey(
        "organization.LegalEntity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    department = models.ForeignKey(
        "organization.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    job_position = models.ForeignKey(
        "organization.JobPosition",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    job_level = models.ForeignKey(
        "organization.JobLevel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )
    default_shift = models.ForeignKey(
        "shifts.Shift",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_employees",
        verbose_name="Shift default",
    )
    manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_reports",
    )
    employee_id = models.CharField(max_length=64, db_index=True)
    barcode = models.CharField(max_length=64, blank=True)
    full_name = models.CharField(max_length=200)
    photo = models.ImageField(
        upload_to="employee_photos/%Y/%m/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )
    nik = EncryptedCharField(max_length=512, blank=True)
    npwp_16_digit = EncryptedCharField(max_length=512, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True, help_text="Mobile Phone (Talenta)")
    phone_landline = models.CharField(max_length=32, blank=True, help_text="Phone (Talenta)")
    address = models.TextField(blank=True, help_text="Residential Address")
    citizen_id_address = models.TextField(blank=True)
    mother_name = models.CharField(max_length=200, blank=True)
    birth_place = models.CharField(max_length=120, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    talenta_age = models.CharField(max_length=32, blank=True, help_text="Age dari export Talenta")

    class Gender(models.TextChoices):
        MALE = "male", "Laki-laki"
        FEMALE = "female", "Perempuan"
        NA = "na", "N/A"

    class MaritalStatus(models.TextChoices):
        SINGLE = "single", "Belum menikah"
        MARRIED = "married", "Menikah"
        DIVORCED = "divorced", "Cerai"
        WIDOWED = "widowed", "Janda/Duda"
        NA = "na", "N/A"

    gender = models.CharField(max_length=16, choices=Gender.choices, blank=True)
    marital_status = models.CharField(
        max_length=16,
        choices=MaritalStatus.choices,
        blank=True,
    )
    join_date = models.DateField(null=True, blank=True)
    sign_date = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(null=True, blank=True, help_text="End Date")
    resign_date = models.DateField(null=True, blank=True)
    status_employee = models.CharField(
        max_length=32,
        blank=True,
        help_text="Status Employee dari export Talenta (Harian, Contract, Permanent).",
    )
    length_of_service = models.CharField(max_length=64, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROBATION,
    )
    salary_scheme = models.CharField(
        max_length=20,
        choices=SalaryScheme.choices,
        default=SalaryScheme.MONTHLY,
    )
    base_salary = EncryptedDecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
    )
    allowance_transport = EncryptedDecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
    )
    allowance_meal = EncryptedDecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
    )
    allowance_position = EncryptedDecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
    )
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account_number = EncryptedCharField(max_length=512, blank=True)
    bank_account_name = EncryptedCharField(max_length=512, blank=True)
    npwp = EncryptedCharField(max_length=512, blank=True)
    tax_status = models.CharField(max_length=16, blank=True, default="")
    pph21_deduct = models.BooleanField(
        null=True,
        blank=True,
        help_text="Null = otomatis potong jika PTKP diisi. False = tidak dipotong.",
    )
    bpjs_kesehatan_number = EncryptedCharField(max_length=512, blank=True)
    bpjs_ketenagakerjaan_number = EncryptedCharField(max_length=512, blank=True)

    employee_tax_status = models.CharField(max_length=64, blank=True)
    tax_config = models.CharField(max_length=64, blank=True)
    passport_number = EncryptedCharField(max_length=512, blank=True)
    passport_expiration_date = models.DateField(null=True, blank=True)
    tax_ref_doc_type = models.CharField(max_length=120, blank=True)
    tax_ref_doc_number = models.CharField(max_length=120, blank=True)
    tax_ref_doc_date = models.DateField(null=True, blank=True)
    tin = EncryptedCharField(max_length=512, blank=True)
    profile_picture_url = models.CharField(max_length=500, blank=True)

    religion = models.ForeignKey(
        TalentaMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees_religion",
        limit_choices_to={"category": TalentaMaster.Category.RELIGION},
    )
    blood_type = models.ForeignKey(
        TalentaMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees_blood_type",
        limit_choices_to={"category": TalentaMaster.Category.BLOOD_TYPE},
    )
    nationality = models.ForeignKey(
        TalentaMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees_nationality",
        limit_choices_to={"category": TalentaMaster.Category.NATIONALITY},
    )
    currency = models.ForeignKey(
        TalentaMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees_currency",
        limit_choices_to={"category": TalentaMaster.Category.CURRENCY},
    )
    payment_schedule = models.ForeignKey(
        TalentaMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees_payment_schedule",
        limit_choices_to={"category": TalentaMaster.Category.PAYMENT_SCHEDULE},
    )
    approval_line = models.ForeignKey(
        TalentaMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees_approval_line",
        limit_choices_to={"category": TalentaMaster.Category.APPROVAL_LINE},
    )
    grade = models.ForeignKey(
        TalentaMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees_grade",
        limit_choices_to={"category": TalentaMaster.Category.GRADE},
    )
    talenta_class = models.ForeignKey(
        TalentaMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees_class",
        limit_choices_to={"category": TalentaMaster.Category.EMPLOYEE_CLASS},
    )
    cost_center = models.ForeignKey(
        TalentaMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees_cost_center",
        limit_choices_to={"category": TalentaMaster.Category.COST_CENTER},
    )
    cost_center_category = models.ForeignKey(
        TalentaMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees_cost_center_category",
        limit_choices_to={"category": TalentaMaster.Category.COST_CENTER_CATEGORY},
    )
    sbu = models.ForeignKey(
        TalentaMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees_sbu",
        limit_choices_to={"category": TalentaMaster.Category.SBU},
    )
    employee_tax_status_master = models.ForeignKey(
        TalentaMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees_tax_status",
        limit_choices_to={"category": TalentaMaster.Category.EMPLOYEE_TAX_STATUS},
    )
    tax_config_master = models.ForeignKey(
        TalentaMaster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees_tax_config",
        limit_choices_to={"category": TalentaMaster.Category.TAX_CONFIG},
    )

    class Meta:
        ordering = ["full_name"]
        unique_together = [["tenant", "employee_id"]]
        indexes = [
            models.Index(fields=["tenant", "plant", "status"]),
            models.Index(fields=["tenant", "nik"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"

    def clean(self):
        super().clean()
        if self.default_shift_id and self.tenant_id:
            if self.default_shift.tenant_id != self.tenant_id:
                raise ValidationError(
                    {"default_shift": "Shift must belong to the same company."}
                )
        if self.plant_id:
            if self.department_id and self.department.plant_id != self.plant_id:
                raise ValidationError(
                    {"department": "Organization harus berada di branch yang sama."}
                )
            if self.job_position_id and self.job_position.plant_id != self.plant_id:
                raise ValidationError(
                    {"job_position": "Job position harus berada di branch yang sama."}
                )
        if self.manager_id and self.manager.tenant_id != self.tenant_id:
            raise ValidationError({"manager": "Manager harus dalam tenant yang sama."})

    @staticmethod
    def _talenta_scalar(value: str | None) -> str:
        text = (value or "").strip()
        if text.upper() in {"N/A", "NA"}:
            return ""
        return text

    @property
    def uses_pph21(self) -> bool:
        if self.pph21_deduct is False:
            return False
        return bool(self.tax_status)

    @property
    def organization_name(self) -> str:
        return self.department.name if self.department_id else ""

    @property
    def branch_name(self) -> str:
        return self.plant.name if self.plant_id else ""

    @property
    def parent_branch_name(self) -> str:
        if self.plant_id and self.plant.parent_id:
            return self.plant.parent.name
        return ""

    def talenta_export_row(self) -> dict[str, str]:
        """Nilai per kolom export Talenta (Employee Database)."""
        from apps.core.listing import format_date
        from apps.employees.talenta_mapping import TALENTA_EMPLOYEE_COLUMNS
        from apps.employees.talenta_vocabulary import TALENTA_COLUMNS

        values = {
            "Employee ID": self.employee_id,
            "Full Name": self.full_name,
            "Organization": self.organization_name,
            "Job Position": self.job_position.title if self.job_position_id else "",
            "Job Level": self.job_level.name if self.job_level_id else "",
            "Join Date": format_date(self.join_date) if self.join_date else "",
            "Resign Date": format_date(self.resign_date) if self.resign_date else "",
            "Status Employee": self.get_status_employee_display(),
            "End Date": format_date(self.contract_end_date) if self.contract_end_date else "",
            "Sign Date": format_date(self.sign_date) if self.sign_date else "",
            "Email": self._talenta_scalar(self.email),
            "Birth Date": format_date(self.birth_date) if self.birth_date else "",
            "Age": self.talenta_age or "",
            "Birth Place": self.birth_place or "",
            "Citizen ID Address": self.citizen_id_address or "",
            "Residential Address": (self.address or "").replace("\n", " "),
            "NPWP": self._talenta_scalar(self.npwp),
            "PTKP Status": self._talenta_scalar(self.tax_status),
            "Employee Tax Status": self.employee_tax_status or (
                self.employee_tax_status_master.name if self.employee_tax_status_master_id else ""
            ),
            "Tax Config": self.tax_config or (
                self.tax_config_master.name if self.tax_config_master_id else ""
            ),
            "Bank Name": self._talenta_scalar(self.bank_name),
            "Bank Account": self._talenta_scalar(self.bank_account_number),
            "Bank Account Holder": self._talenta_scalar(self.bank_account_name),
            "BPJS Ketenagakerjaan": self._talenta_scalar(self.bpjs_ketenagakerjaan_number),
            "BPJS Kesehatan": self._talenta_scalar(self.bpjs_kesehatan_number),
            "NIK (NPWP 16 Digit)": self._talenta_scalar(self.nik),
            "Mobile Phone": self.phone or "",
            "Phone": self.phone_landline or "",
            "Branch Name": self.branch_name,
            "Parent Branch Name": self.parent_branch_name,
            "Religion": self.religion.name if self.religion_id else "",
            "Gender": self.get_gender_excel_display(),
            "Marital Status": self.get_marital_status_excel_display(),
            "Blood Type": self.blood_type.name if self.blood_type_id else "",
            "Nationality Code": self.nationality.name if self.nationality_id else "",
            "Currency": self.currency.name if self.currency_id else "",
            "Length Of Service": self.length_of_service or "",
            "Payment Schedule": self.payment_schedule.name if self.payment_schedule_id else "",
            "Approval Line": self.approval_line.name if self.approval_line_id else "",
            "Manager": self.manager.full_name if self.manager_id else "",
            "Grade": self.grade.name if self.grade_id else "",
            "Class": self.talenta_class.name if self.talenta_class_id else "",
            "Profile Picture": self.profile_picture_url or "",
            "Cost Center": self.cost_center.name if self.cost_center_id else "",
            "Cost Center Category": self.cost_center_category.name if self.cost_center_category_id else "",
            "SBU": self.sbu.name if self.sbu_id else "",
            "NPWP 16 digit (new)": self._talenta_scalar(self.npwp_16_digit),
            "Passport": self._talenta_scalar(self.passport_number),
            "Passport Expiration Date": format_date(self.passport_expiration_date)
            if self.passport_expiration_date
            else "",
            "Jenis Dok. Referensi Bukti Potong": self.tax_ref_doc_type or "",
            "Nomor Dok. Referensi Bukti Potong": self.tax_ref_doc_number or "",
            "Tanggal Dok. Referensi Bukti Potong": format_date(self.tax_ref_doc_date)
            if self.tax_ref_doc_date
            else "",
            "TIN (Taxpayer Identification Number)": self._talenta_scalar(self.tin),
        }
        values["Barcode"] = self.barcode or ""
        return {col: values.get(col, "") for col in TALENTA_COLUMNS}

    def get_gender_excel_display(self) -> str:
        from apps.employees.talenta_vocabulary import gender_to_excel

        return gender_to_excel(self.gender)

    def get_marital_status_excel_display(self) -> str:
        if self.marital_status == self.MaritalStatus.WIDOWED and self.gender == self.Gender.MALE:
            return "Widower"
        from apps.employees.talenta_vocabulary import marital_to_excel

        return marital_to_excel(self.marital_status)

    def get_status_employee_display(self) -> str:
        if self.status_employee:
            return self.status_employee
        if self.status == self.Status.RESIGNED:
            return "Resigned"
        if self.status == self.Status.CONTRACT:
            return "Contract"
        if self.status == self.Status.PERMANENT and self.salary_scheme == self.SalaryScheme.DAILY:
            return "Harian"
        if self.status == self.Status.PERMANENT:
            return "Permanent"
        return self.get_status_display()


class EmployeeDocument(TenantScopedModel):
    """Tier C scaffold — document management."""

    class DocumentType(models.TextChoices):
        KTP = "ktp", "KTP"
        KK = "kk", "KK"
        NPWP = "npwp", "NPWP"
        CONTRACT = "contract", "Contract"
        DIPLOMA = "diploma", "Diploma"
        BPJS = "bpjs", "BPJS Card"
        OTHER = "other", "Other"

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    file = models.FileField(upload_to="employee_documents/%Y/%m/")
    expiry_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.employee.employee_id} — {self.document_type}"

    def clean(self):
        super().clean()
        if self.file and self.file.size > 1024 * 1024:
            raise ValidationError({"file": "Ukuran file maksimal 1 MB."})
