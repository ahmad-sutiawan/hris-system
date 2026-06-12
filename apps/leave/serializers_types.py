from rest_framework import serializers

from apps.leave.models import LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = [
            "id",
            "code",
            "name",
            "is_paid",
            "default_quota_days",
            "requires_attachment",
            "is_active",
        ]
