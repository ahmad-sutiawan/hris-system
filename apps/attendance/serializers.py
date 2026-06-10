from rest_framework import serializers

from apps.attendance.models import AttendanceRecord, DailyTimesheet


class AttendanceRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = [
            "id",
            "employee",
            "employee_name",
            "plant",
            "shift_assignment",
            "work_date",
            "check_in",
            "check_out",
            "source",
            "attendance_code",
            "notes",
        ]


class DailyTimesheetSerializer(serializers.ModelSerializer):
    employee_id = serializers.CharField(source="employee.employee_id", read_only=True)
    full_name = serializers.CharField(source="employee.full_name", read_only=True)
    branch = serializers.CharField(source="plant.code", read_only=True)
    organization = serializers.CharField(source="employee.department.name", read_only=True)
    job_position = serializers.CharField(source="employee.job_position.title", read_only=True)

    class Meta:
        model = DailyTimesheet
        fields = [
            "id",
            "employee",
            "employee_id",
            "full_name",
            "branch",
            "organization",
            "job_position",
            "work_date",
            "shift",
            "shift_code",
            "shift_label",
            "scheduled_check_in",
            "scheduled_check_out",
            "attendance_code",
            "time_off_code",
            "check_in",
            "check_out",
            "late_in_minutes",
            "early_out_minutes",
            "schedule_working_hours",
            "actual_working_hours",
            "paid_working_hours",
            "ot_before_minutes",
            "ot_after_minutes",
            "hourly_time_off_taken",
            "hourly_time_off_breakdown",
            "calculation_status",
        ]
