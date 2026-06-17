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


class Pph21TerCategory(TenantScopedModel):
    """Kategori TER bulanan PP 58/2023 (A, B, C)."""

    code = models.CharField(max_length=1)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        unique_together = [["tenant", "code"]]
        verbose_name = "Kategori TER PPh 21"
        verbose_name_plural = "Kategori TER PPh 21"

    def __str__(self):
        return f"TER {self.code} — {self.name}"


class Pph21TerPtkpMapping(TenantScopedModel):
    """Pemetaan status PTKP ke kategori TER."""

    category = models.ForeignKey(
        Pph21TerCategory,
        on_delete=models.CASCADE,
        related_name="ptkp_mappings",
    )
    ptkp_code = models.CharField(max_length=16)

    class Meta:
        ordering = ["ptkp_code"]
        unique_together = [["tenant", "ptkp_code"]]
        verbose_name = "PTKP → TER"
        verbose_name_plural = "PTKP → TER"

    def __str__(self):
        return f"{self.ptkp_code} → TER {self.category.code}"


class Pph21TerBracket(TenantScopedModel):
    """Lapisan tarif efektif bulanan per kategori TER."""

    category = models.ForeignKey(
        Pph21TerCategory,
        on_delete=models.CASCADE,
        related_name="brackets",
    )
    bracket_no = models.PositiveSmallIntegerField()
    income_from = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0"))
    income_to = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
    )
    rate = models.DecimalField(max_digits=8, decimal_places=6)

    class Meta:
        ordering = ["category", "bracket_no"]
        unique_together = [["tenant", "category", "bracket_no"]]
        verbose_name = "Lapisan TER PPh 21"
        verbose_name_plural = "Lapisan TER PPh 21"

    def __str__(self):
        upper = f"{self.income_to}" if self.income_to is not None else "∞"
        return f"TER {self.category.code} #{self.bracket_no}: {self.income_from}–{upper}"


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


class ShiftAllowanceRate(TenantScopedModel):
    """Nominal tunjangan shift per kode (maps to Shift.shift_allowance_code)."""

    code = models.CharField(max_length=32)
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        unique_together = [["tenant", "code"]]

    def __str__(self):
        return f"{self.code} — {self.name}"
