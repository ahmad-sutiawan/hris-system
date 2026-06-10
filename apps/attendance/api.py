from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.attendance.models import AttendanceRecord, DailyTimesheet
from apps.attendance.services.punch import PunchError, clock_in, clock_out
from apps.attendance.services.timesheet import recalculate_daily_timesheet
from apps.core.viewsets import TenantScopedViewSet
from apps.attendance.serializers import AttendanceRecordSerializer, DailyTimesheetSerializer


class AttendanceRecordViewSet(TenantScopedViewSet):
    queryset = AttendanceRecord.objects.select_related(
        "employee",
        "plant",
        "shift_assignment",
        "attendance_code",
    )
    serializer_class = AttendanceRecordSerializer
    filterset_fields = ["employee", "plant", "work_date", "source"]

    @action(detail=False, methods=["post"])
    def clock_in(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            return Response({"detail": "No employee profile."}, status=400)
        try:
            record = clock_in(profile, source=AttendanceRecord.Source.MOBILE)
            return Response(AttendanceRecordSerializer(record).data)
        except PunchError as exc:
            return Response({"detail": str(exc)}, status=400)

    @action(detail=False, methods=["post"])
    def clock_out(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            return Response({"detail": "No employee profile."}, status=400)
        try:
            record = clock_out(profile)
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
