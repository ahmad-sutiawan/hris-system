from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.viewsets import TenantScopedViewSet
from apps.leave.models import LeaveBalance, LeaveRequest
from apps.leave.serializers import LeaveBalanceSerializer, LeaveRequestSerializer
from apps.leave.services.leave_workflow import (
    LeaveError,
    approve_leave_request,
    reject_leave_request,
    submit_leave_request,
)


class LeaveRequestViewSet(TenantScopedViewSet):
    queryset = LeaveRequest.objects.select_related("employee", "leave_type", "approver")
    serializer_class = LeaveRequestSerializer
    filterset_fields = ["employee", "status", "leave_type"]

    def perform_create(self, serializer):
        profile = getattr(self.request.user, "employee_profile", None)
        if not profile:
            raise LeaveError("No employee profile linked.")
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
            return Response(LeaveRequestSerializer(leave_req).data)
        except LeaveError as exc:
            return Response({"detail": str(exc)}, status=400)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        leave_req = self.get_object()
        try:
            reject_leave_request(leave_req, request.user, reason=request.data.get("reason", ""))
            return Response(LeaveRequestSerializer(leave_req).data)
        except LeaveError as exc:
            return Response({"detail": str(exc)}, status=400)


class LeaveBalanceViewSet(TenantScopedViewSet):
    queryset = LeaveBalance.objects.select_related("employee", "leave_type")
    serializer_class = LeaveBalanceSerializer
    filterset_fields = ["employee", "leave_type", "year"]
