from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.attendance.models import AttendanceRecord, DailyTimesheet
from apps.attendance.services.photo import PhotoError, decode_selfie
from apps.attendance.services.punch import PunchError, clock_in, clock_out
from apps.attendance.services.import_punches import (
    PunchImportError,
    import_attendance_csv,
    template_csv,
)
from apps.attendance.services.timesheet import recalculate_daily_timesheet
from apps.core.api_scoping import employee_scoped_queryset
from apps.core.permissions import IsAdminOrHR
from apps.core.viewsets import TenantScopedViewSet
from apps.attendance.serializers import AttendanceRecordSerializer, DailyTimesheetSerializer


def _parse_punch_photo(request):
    photo_data = request.data.get("photo") or request.data.get("photo_base64")
    if not photo_data:
        raise PunchError("Foto selfie wajib untuk absensi.")
    try:
        return decode_selfie(photo_data)
    except PhotoError as exc:
        raise PunchError(str(exc)) from exc


class AttendanceRecordViewSet(TenantScopedViewSet):
    queryset = AttendanceRecord.objects.select_related(
        "employee",
        "plant",
        "shift_assignment",
        "attendance_code",
    )
    serializer_class = AttendanceRecordSerializer
    filterset_fields = ["employee", "plant", "work_date", "source"]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        return employee_scoped_queryset(self.request.user, qs)

    @action(detail=False, methods=["get"], permission_classes=[IsAdminOrHR])
    def import_template(self, request):
        from django.http import HttpResponse

        response = HttpResponse(template_csv(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="attendance_import_template.csv"'
        return response

    @action(detail=False, methods=["post"], permission_classes=[IsAdminOrHR])
    def import_csv(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "file required."}, status=400)
        try:
            result = import_attendance_csv(
                request.user.tenant,
                upload.read().decode("utf-8-sig"),
                plant=request.user.plant,
            )
            return Response(result)
        except PunchImportError as exc:
            return Response({"detail": str(exc)}, status=400)

    @action(detail=False, methods=["post"])
    def clock_in(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            return Response({"detail": "No employee profile."}, status=400)
        try:
            photo = _parse_punch_photo(request)
            record = clock_in(profile, source=AttendanceRecord.Source.MOBILE, photo=photo)
            return Response(AttendanceRecordSerializer(record).data)
        except PunchError as exc:
            return Response({"detail": str(exc)}, status=400)

    @action(detail=False, methods=["post"])
    def clock_out(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            return Response({"detail": "No employee profile."}, status=400)
        try:
            photo = _parse_punch_photo(request)
            record = clock_out(profile, photo=photo)
            return Response(AttendanceRecordSerializer(record).data)
        except PunchError as exc:
            return Response({"detail": str(exc)}, status=400)


class DailyTimesheetViewSet(TenantScopedViewSet):
    queryset = DailyTimesheet.objects.select_related(
        "employee",
        "employee__department",
        "employee__job_position",
        "plant",
        "shift",
        "attendance_code",
    )
    serializer_class = DailyTimesheetSerializer
    filterset_fields = ["employee", "plant", "work_date", "calculation_status"]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        return employee_scoped_queryset(self.request.user, qs)

    @action(detail=False, methods=["post"])
    def recalculate(self, request):
        employee_id = request.data.get("employee_id")
        work_date = request.data.get("work_date")
        if not employee_id or not work_date:
            return Response({"detail": "employee_id and work_date required."}, status=400)
        from apps.employees.models import Employee

        employee = Employee.objects.get(pk=employee_id, tenant=request.user.tenant)
        ts = recalculate_daily_timesheet(employee, work_date)
        return Response(DailyTimesheetSerializer(ts).data)
