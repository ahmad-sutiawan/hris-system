from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.core.models import AuditLog, FeatureFlag, Notification, Plant, Tenant, User


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "tenant",
        "user",
        "action",
        "model_name",
        "object_id",
        "integrity_hash",
    )
    list_filter = ("action", "model_name", "tenant")
    search_fields = ("object_repr", "object_id", "integrity_hash")
    readonly_fields = (
        "tenant",
        "user",
        "action",
        "model_name",
        "object_id",
        "object_repr",
        "changes",
        "ip_address",
        "user_agent",
        "integrity_hash",
        "created_at",
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Tenant)
admin.site.register(Plant)
admin.site.register(FeatureFlag)
admin.site.register(Notification)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("HRIS", {"fields": ("tenant", "plant", "role")}),
    )
    list_display = ("username", "email", "role", "tenant", "plant", "is_active")
    list_filter = ("role", "tenant", "plant", "is_active")
