from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.models import Announcement
from apps.core.serializers_extra import AnnouncementSerializer
from apps.core.services.announcements import (
    announcements_for_user,
    dismiss_announcement,
    get_announcement_for_user,
    increment_announcement_views,
)


class AnnouncementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Announcement.objects.none()

    def list(self, request, *args, **kwargs):
        items = announcements_for_user(request.user)
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        announcement = get_announcement_for_user(request.user, int(kwargs["pk"]))
        if not announcement:
            return Response({"detail": "Not found."}, status=404)
        increment_announcement_views(announcement)
        return Response(self.get_serializer(announcement).data)

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        announcement = get_announcement_for_user(request.user, int(pk))
        if not announcement:
            return Response({"detail": "Not found."}, status=404)
        dismiss_announcement(request.user, announcement)
        return Response({"status": "ok"})
