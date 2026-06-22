from datetime import datetime

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.models import AuditLog, Notification
from apps.core.permissions import IsAdminOrHR
from apps.core.querysets import audit_log_list_qs
from apps.core.serializers_extra import AuditLogSerializer, NotificationSerializer
from apps.core.services.notifications import mark_notifications_read
from apps.core.viewsets import TenantScopedViewSet


class AuditLogViewSet(TenantScopedViewSet):
    queryset = audit_log_list_qs(AuditLog.objects.all())
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminOrHR]
    http_method_names = ["get", "head", "options"]
    filterset_fields = ["action", "model_name"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        days = getattr(settings, "HRIS_AUDIT_LIST_DEFAULT_DAYS", 90)
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            qs = qs.filter(created_at__gte=self._parse_date(date_from))
        elif days:
            qs = qs.filter(
                created_at__gte=timezone.now() - timezone.timedelta(days=int(days))
            )
        if date_to:
            qs = qs.filter(created_at__lte=self._parse_date(date_to, end_of_day=True))
        return qs

    @staticmethod
    def _parse_date(value: str, *, end_of_day: bool = False):
        parsed = datetime.strptime(value, "%Y-%m-%d")
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        if end_of_day:
            parsed = parsed.replace(hour=23, minute=59, second=59)
        return parsed


class NotificationViewSet(TenantScopedViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "options", "post"]

    def get_queryset(self):
        return Notification.objects.filter(
            tenant=self.request.user.tenant,
            user=self.request.user,
        )

    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": 'Method "POST" not allowed.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
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
