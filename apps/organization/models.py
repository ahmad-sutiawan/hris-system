from decimal import Decimal

from django.db import models

from apps.core.models.base import TenantScopedModel


class LegalEntity(TenantScopedModel):
    name = models.CharField(max_length=200)
    npwp = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Department(TenantScopedModel):
    plant = models.ForeignKey(
        "core.Plant",
        on_delete=models.CASCADE,
        related_name="departments",
    )
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=200)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = [["tenant", "plant", "code"]]

    def __str__(self):
        return self.name


class JobPosition(TenantScopedModel):
    plant = models.ForeignKey(
        "core.Plant",
        on_delete=models.CASCADE,
        related_name="job_positions",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_positions",
    )
    code = models.CharField(max_length=32)
    title = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]
        unique_together = [["tenant", "plant", "code"]]

    def __str__(self):
        return self.title


class EmployeeGrade(TenantScopedModel):
    """Master golongan karyawan — gaji harian dasar untuk perhitungan gaji & lembur."""

    plant = models.ForeignKey(
        "core.Plant",
        on_delete=models.CASCADE,
        related_name="employee_grades",
    )
    code = models.CharField(max_length=16)
    name = models.CharField(max_length=100)
    daily_wage = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        verbose_name="Gaji harian",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        unique_together = [["tenant", "plant", "code"]]
        verbose_name = "Grade Karyawan"
        verbose_name_plural = "Grade Karyawan"

    def __str__(self):
        return f"{self.code} — {self.name}"

    @property
    def hourly_wage(self) -> Decimal:
        return (self.daily_wage / Decimal("8")).quantize(Decimal("0.01"))
