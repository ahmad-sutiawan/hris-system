from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.models import AuditLog, Notification
from apps.core.permissions import IsAdminOrHR
from apps.core.serializers_extra import AuditLogSerializer, NotificationSerializer
from apps.core.services.notifications import mark_notifications_read
from apps.core.viewsets import TenantScopedViewSet


class AuditLogViewSet(TenantScopedViewSet):
    queryset = AuditLog.objects.select_related("user")
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminOrHR]
    http_method_names = ["get", "head", "options"]
    filterset_fields = ["action", "model_name"]


class NotificationViewSet(TenantScopedViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options", "post"]

    def get_queryset(self):
        return Notification.objects.filter(
            tenant=self.request.user.tenant,
            user=self.request.user,
        )

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        mark_notifications_read(request.user)
        return Response({"status": "ok"})

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        mark_notifications_read(request.user, [notification.pk])
        return Response(NotificationSerializer(notification).data)
