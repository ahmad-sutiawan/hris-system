from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.api_scoping import employee_scoped_queryset
from apps.core.viewsets import TenantScopedViewSet
from apps.leave.models import LeaveBalance, LeaveRequest
from apps.leave.serializers import LeaveBalanceSerializer, LeaveRequestSerializer
from apps.leave.services.leave_workflow import (
    LeaveError,
    approve_leave_request,
    cancel_leave_request,
    reject_leave_request,
    submit_leave_request,
)


class LeaveRequestViewSet(TenantScopedViewSet):
    queryset = LeaveRequest.objects.select_related(
        "employee",
        "employee__manager",
        "leave_type",
        "approver",
    )
    serializer_class = LeaveRequestSerializer
    filterset_fields = ["employee", "status", "leave_type"]
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
            req = submit_leave_request(
                employee=profile,
                leave_type=serializer.validated_data["leave_type"],
                start_date=serializer.validated_data["start_date"],
                end_date=serializer.validated_data["end_date"],
                reason=serializer.validated_data.get("reason", ""),
                is_half_day=serializer.validated_data.get("is_half_day", False),
            )
            serializer.instance = req
        except LeaveError as exc:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(str(exc)) from exc

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        leave_req = self.get_object()
        try:
            approve_leave_request(leave_req, request.user)
            return Response(
                LeaveRequestSerializer(leave_req, context=self.get_serializer_context()).data
            )
        except LeaveError as exc:
            return Response({"detail": str(exc)}, status=400)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        leave_req = self.get_object()
        try:
            reject_leave_request(leave_req, request.user, reason=request.data.get("reason", ""))
            return Response(
                LeaveRequestSerializer(leave_req, context=self.get_serializer_context()).data
            )
        except LeaveError as exc:
            return Response({"detail": str(exc)}, status=400)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        leave_req = self.get_object()
        profile = getattr(request.user, "employee_profile", None)
        if not (
            request.user.is_hr
            or (profile and profile.pk == leave_req.employee_id)
        ):
            return Response({"detail": "Forbidden."}, status=403)
        try:
            cancel_leave_request(leave_req, request.user)
            return Response(
                LeaveRequestSerializer(leave_req, context=self.get_serializer_context()).data
            )
        except LeaveError as exc:
            return Response({"detail": str(exc)}, status=400)


class LeaveBalanceViewSet(TenantScopedViewSet):
    queryset = LeaveBalance.objects.select_related("employee", "leave_type")
    serializer_class = LeaveBalanceSerializer
    filterset_fields = ["employee", "leave_type", "year"]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        return employee_scoped_queryset(self.request.user, qs)
