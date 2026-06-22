from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.attendance.models import AttendanceRecord, DailyTimesheet
from apps.attendance.services.record_prefetch import attendance_record_map
from apps.attendance.services.photo import PhotoError, decode_selfie
from apps.attendance.services.punch import PunchError, clock_in, clock_out
from apps.attendance.services.import_punches import (
    PunchImportError,
    import_attendance_xlsx,
    template_xlsx,
)
from apps.attendance.services.timesheet import recalculate_daily_timesheet
from apps.core.api_scoping import employee_scoped_queryset
from apps.core.permissions import IsAdminOrHR
from apps.core.viewsets import TenantScopedViewSet
from apps.attendance.serializers import AttendanceRecordSerializer, DailyTimesheetSerializer
from apps.attendance.throttles import PunchRateThrottle
from apps.employees.models import Employee


def _parse_punch_photo(request):
    photo_data = request.data.get("photo") or request.data.get("photo_base64")
    if not photo_data:
        raise PunchError("Foto selfie wajib untuk absensi.")
    try:
        return decode_selfie(photo_data)
    except PhotoError as exc:
        raise PunchError(str(exc)) from exc


def attach_punch_records(timesheets, tenant) -> None:
    record_map = attendance_record_map(timesheets, tenant)
    for row in timesheets:
        row._punch_record = record_map.get((row.employee_id, row.work_date))


class TimesheetPagination(PageNumberPagination):
    page_size = 31
    max_page_size = 120
    page_size_query_param = "page_size"


class AttendanceRecordViewSet(TenantScopedViewSet):
    queryset = AttendanceRecord.objects.select_related(
        "employee",
        "plant",
        "shift_assignment",
        "attendance_code",
    )
    serializer_class = AttendanceRecordSerializer
    filterset_fields = ["employee", "plant", "work_date", "source"]
    # POST required for @action clock_in/clock_out; direct create blocked below.
    http_method_names = ["get", "post", "head", "options"]

    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": 'Method "POST" not allowed.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def get_queryset(self):
        qs = super().get_queryset()
        return employee_scoped_queryset(self.request.user, qs)

    @action(detail=False, methods=["get"], permission_classes=[IsAdminOrHR])
    def import_template(self, request):
        from apps.core.xlsx_io import xlsx_http_response

        return xlsx_http_response(template_xlsx(), "attendance_import_template.xlsx")

    @action(detail=False, methods=["post"], permission_classes=[IsAdminOrHR])
    def import_csv(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "file required."}, status=400)
        try:
            result = import_attendance_xlsx(
                request.user.tenant,
                upload.read(),
                plant=request.user.plant,
            )
            return Response(result)
        except PunchImportError as exc:
            return Response({"detail": str(exc)}, status=400)

    @action(detail=False, methods=["post"], throttle_classes=[PunchRateThrottle])
    def clock_in(self, request):
        profile = (
            Employee.objects.select_related("tenant", "plant")
            .filter(user=request.user)
            .first()
        )
        if not profile:
            return Response({"detail": "No employee profile."}, status=400)
        try:
            photo = _parse_punch_photo(request)
            record = clock_in(
                profile,
                source=AttendanceRecord.Source.MOBILE,
                photo=photo,
                latitude=request.data.get("latitude"),
                longitude=request.data.get("longitude"),
                notes=request.data.get("notes") or "",
            )
            return Response(AttendanceRecordSerializer(record, context={"request": request}).data)
        except PunchError as exc:
            return Response({"detail": str(exc)}, status=400)

    @action(detail=False, methods=["post"], throttle_classes=[PunchRateThrottle])
    def clock_out(self, request):
        profile = (
            Employee.objects.select_related("tenant", "plant")
            .filter(user=request.user)
            .first()
        )
        if not profile:
            return Response({"detail": "No employee profile."}, status=400)
        try:
            photo = _parse_punch_photo(request)
            record = clock_out(
                profile,
                source=AttendanceRecord.Source.MOBILE,
                photo=photo,
                latitude=request.data.get("latitude"),
                longitude=request.data.get("longitude"),
                notes=request.data.get("notes") or "",
            )
            return Response(AttendanceRecordSerializer(record, context={"request": request}).data)
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
    pagination_class = TimesheetPagination
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = employee_scoped_queryset(self.request.user, qs)

        work_date_from = self.request.query_params.get("work_date_from")
        work_date_to = self.request.query_params.get("work_date_to")
        if work_date_from:
            qs = qs.filter(work_date__gte=work_date_from)
        if work_date_to:
            qs = qs.filter(work_date__lte=work_date_to)
        if not work_date_from and not work_date_to:
            today = timezone.localdate()
            qs = qs.filter(work_date__gte=today.replace(day=1), work_date__lte=today)
        return qs.order_by("-work_date")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        attach_punch_records([instance], request.user.tenant)
        serializer = self.get_serializer(instance, context=self.get_serializer_context())
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        return Response(
            {"detail": 'Method "POST" not allowed.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        items = list(page) if page is not None else list(queryset)
        attach_punch_records(items, request.user.tenant)
        serializer = self.get_serializer(
            items,
            many=True,
            context=self.get_serializer_context(),
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], permission_classes=[IsAdminOrHR])
    def recalculate(self, request):
        employee_id = request.data.get("employee_id")
        work_date = request.data.get("work_date")
        if not employee_id or not work_date:
            return Response({"detail": "employee_id and work_date required."}, status=400)

        employee = Employee.objects.get(pk=employee_id, tenant=request.user.tenant)
        ts = recalculate_daily_timesheet(employee, work_date)
        attach_punch_records([ts], request.user.tenant)
        return Response(DailyTimesheetSerializer(ts, context={"request": request}).data)
