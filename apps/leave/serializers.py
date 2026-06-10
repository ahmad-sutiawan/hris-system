from rest_framework import serializers

from apps.leave.models import LeaveBalance, LeaveRequest


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)

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
            "created_at",
        ]
        read_only_fields = ["status", "approver", "approved_at", "created_at"]


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
