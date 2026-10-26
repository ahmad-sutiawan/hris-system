from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models.base import TenantScopedModel


class Announcement(TenantScopedModel):
    class Category(models.TextChoices):
        GENERAL = "general", "Umum"
        POLICY = "policy", "Kebijakan"
        HR = "hr", "SDM & HR"
        PAYROLL = "payroll", "Payroll & Benefit"
        SAFETY = "safety", "K3 & Keselamatan"
        EVENT = "event", "Acara & Kegiatan"
        IT = "it", "IT & Sistem"
        URGENT = "urgent", "Penting / Darurat"

    class Priority(models.TextChoices):
        LOW = "low", "Rendah"
        NORMAL = "normal", "Normal"
        HIGH = "high", "Tinggi"
        CRITICAL = "critical", "Kritis"

    title = models.CharField(max_length=200)
    summary = models.CharField(
        max_length=500,
        blank=True,
        help_text="Ringkasan singkat untuk banner dan daftar.",
    )
    body = models.TextField(help_text="Konten lengkap pengumuman.")
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.GENERAL,
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    plant = models.ForeignKey(
        "core.Plant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="announcements",
        help_text="Kosongkan untuk semua plant dalam tenant.",
    )
    target_roles = models.JSONField(
        default=list,
        blank=True,
        help_text="Daftar role yang ditargetkan. Kosong = semua role.",
    )
    tags = models.JSONField(default=list, blank=True)
    publish_start = models.DateTimeField()
    publish_end = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_pinned = models.BooleanField(
        default=False,
        help_text="Tampil di atas pengumuman lain.",
    )
    require_acknowledgment = models.BooleanField(
        default=False,
        help_text="Pengguna harus menutup/mengakui sebelum banner hilang.",
    )
    attachment = models.FileField(upload_to="announcements/%Y/%m/", blank=True)
    external_link = models.URLField(blank=True)
    action_label = models.CharField(
        max_length=80,
        blank=True,
        help_text="Label tombol aksi eksternal, mis. Baca panduan lengkap.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="announcements_created",
    )
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-is_pinned", "-publish_start"]
        indexes = [
            models.Index(fields=["tenant", "is_active", "-publish_start"]),
            models.Index(fields=["tenant", "plant", "is_active"]),
        ]

    def __str__(self):
        return self.title

    @property
    def publish_state_label(self) -> str:
        now = timezone.now()
        if not self.is_active:
            return "Nonaktif"
        if self.publish_start > now:
            return "Terjadwal"
        if self.publish_end and self.publish_end < now:
            return "Berakhir"
        return "Tayang"

    @property
    def reaches_everyone(self) -> bool:
        return self.plant_id is None and not (self.target_roles or [])


class AnnouncementDismissal(models.Model):
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name="dismissals",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="announcement_dismissals",
    )
    dismissed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["announcement", "user"]]
        indexes = [
            models.Index(fields=["user", "announcement"]),
        ]

    def __str__(self):
        return f"{self.user_id} dismissed {self.announcement_id}"
