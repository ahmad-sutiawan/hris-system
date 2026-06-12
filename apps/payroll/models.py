from decimal import Decimal

from django.db import models

from apps.core.models.base import TenantScopedModel


class SalaryComponent(TenantScopedModel):
    class ComponentType(models.TextChoices):
        EARNING = "earning", "Earning"
        DEDUCTION = "deduction", "Deduction"

    code = models.CharField(max_length=32)
    name = models.CharField(max_length=100)
    component_type = models.CharField(max_length=20, choices=ComponentType.choices)
    formula_key = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        unique_together = [["tenant", "code"]]

    def __str__(self):
        return f"{self.code} — {self.name}"


class PayrollRun(TenantScopedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        REVIEW = "review", "Review"
        FINALIZED = "finalized", "Finalized"
        CANCELLED = "cancelled", "Cancelled"

    plant = models.ForeignKey(
        "core.Plant",
        on_delete=models.PROTECT,
        related_name="payroll_runs",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    finalized_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-period_start"]
        unique_together = [["tenant", "plant", "period_start", "period_end"]]

    def __str__(self):
        return f"{self.plant.code} — {self.period_start} to {self.period_end}"


class Payslip(TenantScopedModel):
    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name="payslips",
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="payslips",
    )
    gross_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    deduction_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    net_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    earnings_breakdown = models.JSONField(default=dict, blank=True)
    deductions_breakdown = models.JSONField(default=dict, blank=True)
    pdf_file = models.FileField(upload_to="payslips/%Y/%m/", blank=True)
    verification_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["employee__full_name"]
        unique_together = [["payroll_run", "employee"]]

    def __str__(self):
        return f"{self.employee.employee_id} — {self.payroll_run_id}"


class THRRun(TenantScopedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        FINALIZED = "finalized", "Finalized"

    plant = models.ForeignKey(
        "core.Plant",
        on_delete=models.PROTECT,
        related_name="thr_runs",
    )
    year = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [["tenant", "plant", "year"]]

    def __str__(self):
        return f"THR {self.year} — {self.plant.code}"


class THRPayslip(TenantScopedModel):
    thr_run = models.ForeignKey(
        THRRun,
        on_delete=models.CASCADE,
        related_name="payslips",
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="thr_payslips",
    )
    months_worked = models.PositiveSmallIntegerField(default=12)
    base_reference = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    thr_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

    class Meta:
        unique_together = [["thr_run", "employee"]]
        ordering = ["employee__full_name"]

    def __str__(self):
        return f"THR {self.thr_run.year} — {self.employee.employee_id}"
