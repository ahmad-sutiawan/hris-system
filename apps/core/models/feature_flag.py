from django.db import models

from apps.core.models.base import TimeStampedModel


class FeatureFlag(TimeStampedModel):
    tenant = models.ForeignKey(
        "core.Tenant",
        on_delete=models.CASCADE,
        related_name="feature_flags",
    )
    plant = models.ForeignKey(
        "core.Plant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="feature_flags",
    )
    key = models.CharField(max_length=100)
    enabled = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = [["tenant", "plant", "key"]]
        ordering = ["key"]

    def __str__(self):
        scope = self.plant.code if self.plant_id else "tenant-wide"
        return f"{self.key} ({scope})"
