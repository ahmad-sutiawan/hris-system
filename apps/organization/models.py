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
