from django.db import models

from apps.core.models.base import TenantScopedModel


class PunchLocation(TenantScopedModel):
    """Lokasi absen yang diizinkan (hybrid / multi-site)."""

    plant = models.ForeignKey(
        "core.Plant",
        on_delete=models.CASCADE,
        related_name="punch_locations",
    )
    name = models.CharField(max_length=200)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    radius_m = models.PositiveIntegerField(default=150)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.plant.code})"
