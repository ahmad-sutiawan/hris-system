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
    class BranchType(models.TextChoices):
        BPS_HARIAN = "bps_harian", "PT BPS Harian"
        BPS_STAFF = "bps_staff", "PT BPS Staff"
        SPV_UP = "spv_up", "SPV ke atas"
        OTHER = "other", "Lainnya"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="plants")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    branch_type = models.CharField(
        max_length=32,
        choices=BranchType.choices,
        default=BranchType.OTHER,
        blank=True,
    )
    timezone = models.CharField(max_length=64, default="Asia/Jakarta")
    address = models.TextField(blank=True)
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )
    geo_fence_radius_m = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Radius geo-fence absen (meter). Default 150 jika koordinat diisi.",
    )
    default_shift = models.ForeignKey(
        "shifts.Shift",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_for_plants",
        help_text="Shift otomatis untuk karyawan baru di plant ini.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        unique_together = [["tenant", "code"]]

    def __str__(self):
        return f"{self.code} — {self.name}"
