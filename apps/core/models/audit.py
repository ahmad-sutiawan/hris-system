from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models


class AuditLogQuerySet(models.QuerySet):
    def for_tenant(self, tenant):
        return self.filter(tenant=tenant)

    def recent(self, days: int):
        from django.utils import timezone

        cutoff = timezone.now() - timezone.timedelta(days=days)
        return self.filter(created_at__gte=cutoff)


class AuditLogManager(models.Manager):
    def get_queryset(self):
        return AuditLogQuerySet(self.model, using=self._db)

    def for_tenant(self, tenant):
        return self.get_queryset().for_tenant(tenant)

    def recent(self, days: int):
        return self.get_queryset().recent(days)


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        ACCESS = "access", "Access"

    tenant = models.ForeignKey(
        "core.Tenant",
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=64)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    integrity_hash = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="SHA-256 tamper-evidence hash (append-only records).",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = AuditLogManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "-created_at"], name="audit_tenant_created_idx"),
            models.Index(fields=["tenant", "model_name", "-created_at"], name="audit_tenant_model_idx"),
            models.Index(fields=["tenant", "object_id", "model_name"], name="audit_tenant_object_idx"),
        ]
        permissions = [
            ("purge_auditlog", "Can purge archived audit logs (management command only)"),
        ]

    def __str__(self):
        return f"{self.action} {self.model_name}:{self.object_id}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionDenied("Audit log bersifat append-only dan tidak boleh diubah.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Audit log tidak boleh dihapus via aplikasi. Gunakan perintah archive_audit_logs.")
