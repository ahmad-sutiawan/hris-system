from apps.core.viewsets import TenantScopedViewSet
from apps.leave.models import LeaveType
from apps.leave.serializers_types import LeaveTypeSerializer


class LeaveTypeViewSet(TenantScopedViewSet):
    queryset = LeaveType.objects.filter(is_active=True)
    serializer_class = LeaveTypeSerializer
    http_method_names = ["get", "head", "options"]
    filterset_fields = ["is_paid", "is_active"]
    search_fields = ["code", "name"]
