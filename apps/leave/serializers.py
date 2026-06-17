from rest_framework import serializers

from apps.core.approval import can_approve_request
from apps.leave.models import LeaveBalance, LeaveRequest


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    can_approve = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "employee",
            "employee_name",
            "leave_type",
            "leave_type_code",
            "start_date",
            "end_date",
            "days",
            "is_half_day",
            "reason",
            "status",
            "approver",
            "approved_at",
            "rejection_reason",
            "approval_step",
            "can_approve",
            "created_at",
        ]
        read_only_fields = [
            "employee",
            "days",
            "status",
            "approver",
            "approved_at",
            "rejection_reason",
            "created_at",
        ]

    def get_can_approve(self, obj) -> bool:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        if obj.status != LeaveRequest.Status.PENDING:
            return False
        return can_approve_request(
            request.user,
            obj.employee,
            "leave",
            obj.approval_step or 1,
        )


class LeaveBalanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "employee",
            "employee_name",
            "leave_type",
            "leave_type_code",
            "year",
            "opening_balance",
            "accrued",
            "used",
            "pending",
            "remaining",
        ]
