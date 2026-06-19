from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.attendance.models import OvertimeRequest, OvertimeType
from apps.attendance.serializers_overtime import (
    OvertimeRequestSerializer,
    OvertimeTypeSerializer,
)
from apps.attendance.services.overtime_compensation import build_compensation_preview
from apps.attendance.services.overtime_workflow import (
    OvertimeError,
    approve_overtime_request,
    cancel_overtime_request,
    get_raw_overtime_minutes,
    reject_overtime_request,
    submit_overtime_request,
)
from apps.core.api_scoping import employee_scoped_queryset
from apps.core.viewsets import TenantScopedViewSet


class OvertimeTypeViewSet(TenantScopedViewSet):
    queryset = OvertimeType.objects.filter(is_active=True)
    serializer_class = OvertimeTypeSerializer
    http_method_names = ["get", "head", "options"]
    filterset_fields = ["day_category", "is_active"]
    search_fields = ["code", "name"]


class OvertimeRequestViewSet(TenantScopedViewSet):
    queryset = OvertimeRequest.objects.select_related(
        "employee",
        "employee__manager",
        "overtime_type",
        "approver",
    )
    serializer_class = OvertimeRequestSerializer
    filterset_fields = ["employee", "status", "work_date"]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        return employee_scoped_queryset(self.request.user, qs)

    def perform_create(self, serializer):
        profile = getattr(self.request.user, "employee_profile", None)
        if not profile:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("Akun belum terhubung ke data karyawan.")
        try:
            req = submit_overtime_request(
                employee=profile,
                work_date=serializer.validated_data["work_date"],
                overtime_type=serializer.validated_data.get("overtime_type"),
                ot_before_minutes=serializer.validated_data.get("ot_before_minutes") or 0,
                ot_after_minutes=serializer.validated_data.get("ot_after_minutes") or 0,
                compensation_mode=serializer.validated_data.get(
                    "compensation_mode",
                    OvertimeRequest.CompensationMode.CASH,
                ),
                reason=serializer.validated_data.get("reason", ""),
            )
            serializer.instance = req
        except OvertimeError as exc:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(str(exc)) from exc

    @action(detail=False, methods=["get"])
    def suggested_minutes(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            return Response({"detail": "No employee profile."}, status=400)
        from datetime import datetime

        from django.utils import timezone

        raw_date = request.query_params.get("work_date")
        if raw_date:
            work_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
        else:
            work_date = timezone.localdate()
        before, after = get_raw_overtime_minutes(profile, work_date)
        return Response(
            {
                "work_date": work_date.isoformat(),
                "ot_before_minutes": before,
                "ot_after_minutes": after,
            }
        )

    @action(detail=False, methods=["post"])
    def compensation_preview(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            return Response({"detail": "No employee profile."}, status=400)

        ot_before = int(request.data.get("ot_before_minutes") or 0)
        ot_after = int(request.data.get("ot_after_minutes") or 0)
        overtime_type = None
        type_id = request.data.get("overtime_type")
        if type_id:
            overtime_type = OvertimeType.objects.filter(
                pk=type_id,
                tenant=request.user.tenant,
            ).first()

        return Response(
            build_compensation_preview(
                profile,
                ot_before_minutes=ot_before,
                ot_after_minutes=ot_after,
                overtime_type=overtime_type,
            )
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        overtime_req = self.get_object()
        try:
            overtime_req = approve_overtime_request(overtime_req, request.user)
            return Response(
                OvertimeRequestSerializer(
                    overtime_req, context=self.get_serializer_context()
                ).data
            )
        except OvertimeError as exc:
            return Response({"detail": str(exc)}, status=400)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        overtime_req = self.get_object()
        try:
            reject_overtime_request(
                overtime_req,
                request.user,
                reason=request.data.get("reason", ""),
            )
            return Response(
                OvertimeRequestSerializer(
                    overtime_req, context=self.get_serializer_context()
                ).data
            )
        except OvertimeError as exc:
            return Response({"detail": str(exc)}, status=400)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        overtime_req = self.get_object()
        profile = getattr(request.user, "employee_profile", None)
        if not (
            request.user.is_hr
            or (profile and profile.pk == overtime_req.employee_id)
        ):
            return Response({"detail": "Forbidden."}, status=403)
        try:
            cancel_overtime_request(overtime_req, request.user)
            return Response(
                OvertimeRequestSerializer(
                    overtime_req, context=self.get_serializer_context()
                ).data
            )
        except OvertimeError as exc:
            return Response({"detail": str(exc)}, status=400)
