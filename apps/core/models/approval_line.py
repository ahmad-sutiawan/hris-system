from django.db import models

from apps.core.models.base import TenantScopedModel


class ApprovalLine(TenantScopedModel):
    """Template approval multi-layer per jenis request."""

    class RequestType(models.TextChoices):
        LEAVE = "leave", "Cuti"
        OVERTIME = "overtime", "Lembur"
        ATTENDANCE_CORRECTION = "attendance_correction", "Koreksi absensi"

    class ApproverKind(models.TextChoices):
        DIRECT_MANAGER = "direct_manager", "Atasan langsung"
        HR_PLANT = "hr_plant", "HR plant"
        HR_TENANT = "hr_tenant", "HR tenant"

    request_type = models.CharField(max_length=32, choices=RequestType.choices)
    step_order = models.PositiveSmallIntegerField(default=1)
    approver_kind = models.CharField(max_length=32, choices=ApproverKind.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["request_type", "step_order"]
        unique_together = [["tenant", "request_type", "step_order"]]

    def __str__(self):
        return f"{self.request_type} step {self.step_order} ({self.approver_kind})"
