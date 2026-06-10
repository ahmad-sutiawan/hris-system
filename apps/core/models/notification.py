from django.db import models

from apps.core.models.base import TenantScopedModel


class Notification(TenantScopedModel):
    class Category(models.TextChoices):
        LEAVE = "leave", "Leave"
        PAYROLL = "payroll", "Payroll"
        ATTENDANCE = "attendance", "Attendance"
        SYSTEM = "system", "System"

    user = models.ForeignKey(
        "core.User",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "user", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.title}"
