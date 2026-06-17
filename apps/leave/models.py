from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.core.models.base import TenantScopedModel


class LeaveType(TenantScopedModel):
    code = models.CharField(max_length=16)
    name = models.CharField(max_length=100)
    is_paid = models.BooleanField(default=True)
    default_quota_days = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("12"),
    )
    requires_attachment = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        unique_together = [["tenant", "code"]]

    def __str__(self):
        return f"{self.code} — {self.name}"


class LeaveBalance(TenantScopedModel):
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="leave_balances",
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name="balances",
    )
    year = models.PositiveIntegerField()
    opening_balance = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    accrued = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    used = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    pending = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))
    remaining = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0"))

    class Meta:
        unique_together = [["employee", "leave_type", "year"]]
        ordering = ["-year", "leave_type"]

    def __str__(self):
        return f"{self.employee.employee_id} — {self.leave_type.code} ({self.year})"


class LeaveRequest(TenantScopedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="leave_requests",
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="requests",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1"))
    is_half_day = models.BooleanField(default=False)
    reason = models.TextField(blank=True)
    attachment = models.FileField(upload_to="leave_attachments/%Y/%m/", blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leave_requests",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    approval_step = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.employee.employee_id} — {self.leave_type.code}"


class LeaveHourlySegment(TenantScopedModel):
    """Tier C scaffold — hourly leave breakdown."""

    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name="hourly_segments",
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    hours = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.leave_request_id} — {self.hours}h"
