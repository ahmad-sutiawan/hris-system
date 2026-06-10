from apps.core.viewsets import TenantScopedViewSet
from apps.shifts.models import Shift, ShiftAssignment
from apps.shifts.serializers import ShiftAssignmentSerializer, ShiftSerializer


class ShiftViewSet(TenantScopedViewSet):
    queryset = Shift.objects.select_related("plant")
    serializer_class = ShiftSerializer
    filterset_fields = ["plant", "is_active"]
    search_fields = ["code", "name"]


class ShiftAssignmentViewSet(TenantScopedViewSet):
    queryset = ShiftAssignment.objects.select_related("employee", "shift")
    serializer_class = ShiftAssignmentSerializer
    filterset_fields = ["employee", "work_date", "shift"]
