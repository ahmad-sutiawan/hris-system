from rest_framework import serializers

from apps.attendance.models import AttendancePunch, AttendanceRecord, DailyTimesheet
from apps.core.media_serving import build_media_url


def _photo_url(record: AttendanceRecord | AttendancePunch | None, field: str, request) -> str | None:
    if not record:
        return None
    image = getattr(record, field, None)
    if not image or not image.name:
        return None
    return build_media_url(image.name, request=request)


class AttendancePunchSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = AttendancePunch
        fields = [
            "id",
            "punch_type",
            "punched_at",
            "source",
            "photo_url",
            "notes",
        ]

    def get_photo_url(self, obj):
        return _photo_url(obj, "photo", self.context.get("request"))


class AttendanceRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    check_in_photo_url = serializers.SerializerMethodField()
    check_out_photo_url = serializers.SerializerMethodField()

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
            "check_in_photo_url",
            "check_out_photo_url",
        ]

    def get_check_in_photo_url(self, obj):
        return _photo_url(obj, "check_in_photo", self.context.get("request"))

    def get_check_out_photo_url(self, obj):
        return _photo_url(obj, "check_out_photo", self.context.get("request"))


class DailyTimesheetSerializer(serializers.ModelSerializer):
    employee_id = serializers.CharField(source="employee.employee_id", read_only=True)
    full_name = serializers.CharField(source="employee.full_name", read_only=True)
    branch = serializers.CharField(source="plant.code", read_only=True)
    organization = serializers.CharField(source="employee.department.name", read_only=True)
    job_position = serializers.CharField(source="employee.job_position.title", read_only=True)
    attendance_code_label = serializers.CharField(
        source="attendance_code.code",
        read_only=True,
        allow_null=True,
        default=None,
    )
    check_in_photo_url = serializers.SerializerMethodField()
    check_out_photo_url = serializers.SerializerMethodField()
    punch_source = serializers.SerializerMethodField()
    punch_events = serializers.SerializerMethodField()

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
            "attendance_code_label",
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
            "check_in_photo_url",
            "check_out_photo_url",
            "punch_source",
            "punch_events",
        ]

    def _punch_record(self, obj):
        return getattr(obj, "_punch_record", None)

    def get_check_in_photo_url(self, obj):
        return _photo_url(self._punch_record(obj), "check_in_photo", self.context.get("request"))

    def get_check_out_photo_url(self, obj):
        return _photo_url(self._punch_record(obj), "check_out_photo", self.context.get("request"))

    def get_punch_source(self, obj):
        record = self._punch_record(obj)
        return record.source if record else None

    def get_punch_events(self, obj):
        record = self._punch_record(obj)
        if not record:
            return []
        punches = getattr(record, "_prefetched_punches", None)
        if punches is None:
            punches = record.punches.order_by("punched_at", "pk")
        return AttendancePunchSerializer(
            punches,
            many=True,
            context=self.context,
        ).data
