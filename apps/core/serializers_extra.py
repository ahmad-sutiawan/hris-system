from rest_framework import serializers

from apps.core.models import Announcement, AuditLog, Notification


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "action",
            "model_name",
            "object_id",
            "object_repr",
            "changes",
            "user_name",
            "ip_address",
            "created_at",
        ]


class AnnouncementSerializer(serializers.ModelSerializer):
    plant_name = serializers.CharField(source="plant.name", read_only=True, default=None)
    is_dismissed = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [
            "id",
            "title",
            "summary",
            "body",
            "category",
            "priority",
            "plant",
            "plant_name",
            "tags",
            "publish_start",
            "publish_end",
            "is_pinned",
            "require_acknowledgment",
            "external_link",
            "action_label",
            "view_count",
            "is_dismissed",
        ]

    def get_is_dismissed(self, obj) -> bool:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.dismissals.filter(user=request.user).exists()


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "category",
            "title",
            "message",
            "link",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = ["read_at", "created_at"]
