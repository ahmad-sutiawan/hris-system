from rest_framework import serializers

from apps.shifts.models import Shift, ShiftAssignment


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = [
            "id",
            "name",
            "code",
            "label",
            "scheduled_check_in",
            "scheduled_check_out",
            "break_minutes",
            "grace_period_minutes",
            "schedule_working_hours",
            "cross_day",
            "is_active",
        ]


class ShiftAssignmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    shift_code = serializers.CharField(source="shift.code", read_only=True)

    class Meta:
        model = ShiftAssignment
        fields = [
            "id",
            "employee",
            "employee_name",
            "shift",
            "shift_code",
            "work_date",
            "scheduled_check_in",
            "scheduled_check_out",
        ]
