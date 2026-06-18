from decimal import Decimal

from django.db import models

from apps.core.models.base import TenantScopedModel


class Shift(TenantScopedModel):
    plant = models.ForeignKey(
        "core.Plant",
        on_delete=models.CASCADE,
        related_name="shifts",
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=32)
    label = models.CharField(max_length=100, blank=True)
    scheduled_check_in = models.TimeField()
    scheduled_check_out = models.TimeField()
    break_minutes = models.PositiveIntegerField(default=60)
    grace_period_minutes = models.PositiveIntegerField(default=15)
    schedule_working_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("8.00"),
    )
    cross_day = models.BooleanField(
        default=False,
        help_text="Night shift: clock in on work date, clock out the next calendar day.",
    )
    shift_allowance_code = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        unique_together = [["tenant", "plant", "code"]]

    def __str__(self):
        return f"{self.code} — {self.name}"

    def save(self, *args, **kwargs):
        if self.scheduled_check_in and self.scheduled_check_out:
            if self.scheduled_check_out <= self.scheduled_check_in:
                self.cross_day = True
        super().save(*args, **kwargs)


class ShiftAssignment(TenantScopedModel):
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="shift_assignments",
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    work_date = models.DateField(db_index=True)
    scheduled_check_in = models.TimeField()
    scheduled_check_out = models.TimeField()

    class Meta:
        ordering = ["-work_date"]
        unique_together = [["employee", "work_date"]]

    def __str__(self):
        return f"{self.employee.employee_id} — {self.work_date}"


class ShiftRotationTemplate(TenantScopedModel):
    """Tier C scaffold — rotating shift generator."""

    plant = models.ForeignKey(
        "core.Plant",
        on_delete=models.CASCADE,
        related_name="shift_rotation_templates",
    )
    name = models.CharField(max_length=200)
    cycle_weeks = models.PositiveIntegerField(default=4)
    pattern = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.name

