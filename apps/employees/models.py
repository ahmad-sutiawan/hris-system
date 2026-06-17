from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from apps.core.fields import EncryptedCharField, EncryptedDecimalField
from apps.core.models.base import TenantScopedModel


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
    full_name = models.CharField(max_length=200)
    photo = models.ImageField(
        upload_to="employee_photos/%Y/%m/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
    )
    nik = EncryptedCharField(max_length=512, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    address = models.TextField(blank=True)
    mother_name = models.CharField(max_length=200, blank=True)
    birth_place = models.CharField(max_length=120, blank=True)
    birth_date = models.DateField(null=True, blank=True)

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
    contract_end_date = models.DateField(null=True, blank=True)
    resign_date = models.DateField(null=True, blank=True)
    status_employee = models.CharField(
        max_length=32,
        blank=True,
        help_text="Status Employee dari export Talenta (Harian, Contract, Permanent).",
    )
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
        if self.default_shift_id and self.plant_id:
            if self.default_shift.plant_id != self.plant_id:
                raise ValidationError(
                    {"default_shift": "Shift harus dari plant yang sama."}
                )

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
        from apps.employees.talenta_vocabulary import parent_branch_name

        return parent_branch_name(self.branch_name)

    def get_gender_excel_display(self) -> str:
        from apps.employees.talenta_vocabulary import gender_to_excel

        return gender_to_excel(self.gender)

    def get_marital_status_excel_display(self) -> str:
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
