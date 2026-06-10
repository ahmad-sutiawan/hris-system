from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.core.models import AuditLog, FeatureFlag, Notification, Plant, Tenant, User

admin.site.register(Tenant)
admin.site.register(Plant)
admin.site.register(FeatureFlag)
admin.site.register(AuditLog)
admin.site.register(Notification)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("HRIS", {"fields": ("tenant", "plant", "role")}),
    )
    list_display = ("username", "email", "role", "tenant", "plant", "is_active")
    list_filter = ("role", "tenant", "plant", "is_active")
