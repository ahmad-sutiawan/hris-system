from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        HR = "hr", "HR"
        MANAGER = "manager", "Manager"
        EMPLOYEE = "employee", "Employee"
        FINANCE = "finance", "Finance"
        AUDITOR = "auditor", "Auditor"

    tenant = models.ForeignKey(
        "core.Tenant",
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )
    plant = models.ForeignKey(
        "core.Plant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "role"]),
        ]

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_hr(self):
        return self.role in {self.Role.ADMIN, self.Role.HR}
