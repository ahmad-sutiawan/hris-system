from django.db import models

from apps.core.models.base import TimeStampedModel


class Tenant(TimeStampedModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Plant(TimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="plants")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    timezone = models.CharField(max_length=64, default="Asia/Jakarta")
    address = models.TextField(blank=True)
    geo_fence_radius_m = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Tier C: GPS geo-fence radius in meters",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        unique_together = [["tenant", "code"]]

    def __str__(self):
        return f"{self.code} — {self.name}"
