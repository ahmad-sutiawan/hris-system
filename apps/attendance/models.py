from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.core.models.base import TenantScopedModel


class AttendanceCode(TenantScopedModel):
    class PayrollImpact(models.TextChoices):
        PAID = "paid", "Paid"
        UNPAID = "unpaid", "Unpaid"
        DEDUCT = "deduct", "Deduction"
        NONE = "none", "None"

    code = models.CharField(max_length=8)
    label = models.CharField(max_length=100)
    payroll_impact = models.CharField(
        max_length=20,
        choices=PayrollImpact.choices,
        default=PayrollImpact.NONE,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        unique_together = [["tenant", "code"]]

    def __str__(self):
        return f"{self.code} — {self.label}"


class AttendanceRecord(TenantScopedModel):
    class Source(models.TextChoices):
        WEB = "web", "Web"
        MOBILE = "mobile", "Mobile"
        KIOSK = "kiosk", "Kiosk"
        IMPORT = "import", "Import"
        MANUAL = "manual", "Manual"

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    plant = models.ForeignKey(
        "core.Plant",
        on_delete=models.PROTECT,
        related_name="attendance_records",
    )
    shift_assignment = models.ForeignKey(
        "shifts.ShiftAssignment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
    )
    work_date = models.DateField(db_index=True)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.WEB)
    attendance_code = models.ForeignKey(
        AttendanceCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_attendance_records",
    )

    class Meta:
        ordering = ["-work_date", "employee"]
        indexes = [
            models.Index(fields=["tenant", "plant", "work_date"]),
        ]

    def __str__(self):
        return f"{self.employee.employee_id} — {self.work_date}"


class DailyTimesheet(TenantScopedModel):
    class CalculationStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        FINALIZED = "finalized", "Finalized"
        LOCKED = "locked", "Locked"

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="daily_timesheets",
    )
    plant = models.ForeignKey(
        "core.Plant",
        on_delete=models.PROTECT,
        related_name="daily_timesheets",
    )
    work_date = models.DateField(db_index=True)
    shift = models.ForeignKey(
        "shifts.Shift",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="daily_timesheets",
    )
    shift_code = models.CharField(max_length=32, blank=True)
    shift_label = models.CharField(max_length=100, blank=True)
    scheduled_check_in = models.TimeField(null=True, blank=True)
    scheduled_check_out = models.TimeField(null=True, blank=True)
    attendance_code = models.ForeignKey(
        AttendanceCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="daily_timesheets",
    )
    time_off_code = models.CharField(max_length=32, blank=True)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    late_in_minutes = models.PositiveIntegerField(default=0)
    early_out_minutes = models.PositiveIntegerField(default=0)
    schedule_working_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0"),
    )
    actual_working_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0"),
    )
    paid_working_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0"),
    )
    ot_before_minutes = models.PositiveIntegerField(default=0)
    ot_after_minutes = models.PositiveIntegerField(default=0)
    hourly_time_off_taken = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0"),
    )
    hourly_time_off_breakdown = models.JSONField(default=list, blank=True)
    calculation_status = models.CharField(
        max_length=20,
        choices=CalculationStatus.choices,
        default=CalculationStatus.DRAFT,
    )
    calculated_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-work_date", "employee"]
        unique_together = [["employee", "work_date"]]
        indexes = [
            models.Index(fields=["tenant", "plant", "work_date"]),
        ]

    def __str__(self):
        return f"{self.employee.employee_id} — {self.work_date}"
