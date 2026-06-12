from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
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
    employee_grade = models.ForeignKey(
        "organization.EmployeeGrade",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
        verbose_name="Grade karyawan",
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
    nik = EncryptedCharField(max_length=512, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    join_date = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(null=True, blank=True)
    resign_date = models.DateField(null=True, blank=True)
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
    tax_status = models.CharField(max_length=16, blank=True)
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
        if self.employee_grade_id and self.plant_id:
            if self.employee_grade.plant_id != self.plant_id:
                raise ValidationError(
                    {"employee_grade": "Grade karyawan harus dari plant yang sama."}
                )

    @property
    def grade_label(self) -> str:
        if self.employee_grade_id:
            return f"{self.employee_grade.code} — {self.employee_grade.name}"
        return ""


class EmployeeDocument(TenantScopedModel):
    """Tier C scaffold — document management."""

    class DocumentType(models.TextChoices):
        KTP = "ktp", "KTP"
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
