from rest_framework import viewsets

from apps.core.permissions import IsTenantUser


class TenantScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [IsTenantUser]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_admin:
            return qs.filter(tenant=user.tenant)
        if user.plant_id:
            if hasattr(qs.model, "plant"):
                return qs.filter(tenant=user.tenant, plant=user.plant)
            if hasattr(qs.model, "employee"):
                return qs.filter(tenant=user.tenant, employee__plant=user.plant)
        return qs.filter(tenant=user.tenant)

    def perform_create(self, serializer):
        extra = {"tenant": self.request.user.tenant}
        if hasattr(serializer.Meta.model, "plant") and self.request.user.plant_id:
            extra["plant"] = self.request.user.plant
        serializer.save(**extra)
