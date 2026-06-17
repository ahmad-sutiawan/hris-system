from rest_framework import serializers

from apps.attendance.models import OvertimeRequest, OvertimeType
from apps.core.approval import can_approve_employee


class OvertimeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OvertimeType
        fields = [
            "id",
            "code",
            "name",
            "day_category",
            "hour_from",
            "hour_to",
            "multiplier",
            "is_active",
        ]


class OvertimeRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    overtime_type_name = serializers.CharField(source="overtime_type.name", read_only=True)
    overtime_type_code = serializers.CharField(source="overtime_type.code", read_only=True)
    can_approve = serializers.SerializerMethodField()

    class Meta:
        model = OvertimeRequest
        fields = [
            "id",
            "employee",
            "employee_name",
            "overtime_type",
            "overtime_type_name",
            "overtime_type_code",
            "work_date",
            "ot_before_minutes",
            "ot_after_minutes",
            "compensation_mode",
            "leave_days_credited",
            "reason",
            "status",
            "approver",
            "approved_at",
            "rejection_reason",
            "can_approve",
            "created_at",
        ]
        read_only_fields = [
            "employee",
            "status",
            "approver",
            "approved_at",
            "leave_days_credited",
            "rejection_reason",
            "created_at",
        ]

    def get_can_approve(self, obj) -> bool:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        if obj.status != OvertimeRequest.Status.PENDING:
            return False
        return can_approve_employee(request.user, obj.employee)
