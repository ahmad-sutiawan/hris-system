from django.db import models

from apps.core.models.base import TenantScopedModel


class HolidayCalendar(TenantScopedModel):
    """Libur nasional / company holiday — absen tetap diizinkan untuk tracking OT."""

    class HolidayType(models.TextChoices):
        NATIONAL = "national", "Libur nasional"
        COMPANY = "company", "Libur perusahaan"
        PLANT = "plant", "Libur plant"

    name = models.CharField(max_length=200)
    holiday_date = models.DateField()
    holiday_type = models.CharField(
        max_length=20,
        choices=HolidayType.choices,
        default=HolidayType.NATIONAL,
    )
    plant = models.ForeignKey(
        "core.Plant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="holidays",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-holiday_date"]
        unique_together = [["tenant", "holiday_date", "name"]]

    def __str__(self):
        return f"{self.holiday_date} — {self.name}"
