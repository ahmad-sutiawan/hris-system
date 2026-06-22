from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.api_scoping import employee_scoped_queryset
from apps.core.permissions import IsAdminOrHR, IsTenantUser
from apps.core.querysets import employee_list_qs
from apps.core.viewsets import TenantScopedViewSet
from apps.employees.models import Employee
from apps.employees.serializers import (
    EmployeeDirectorySerializer,
    EmployeeSelfSerializer,
    EmployeeSerializer,
)
from apps.employees.services.import_csv import template_xlsx
from apps.employees.services.import_dispatch import import_employees_file


class EmployeeViewSet(TenantScopedViewSet):
    queryset = employee_list_qs(Employee.objects.all())
    serializer_class = EmployeeSerializer
    search_fields = ["employee_id", "full_name", "nik", "email"]
    filterset_fields = ["plant", "department", "job_position", "status"]

    def get_permissions(self):
        if self.action in ("list", "retrieve", "me"):
            return [IsTenantUser()]
        return [IsAdminOrHR()]

    def get_serializer_class(self):
        user = self.request.user
        if self.action in ("list", "retrieve") and not (user.is_hr or user.is_admin):
            return EmployeeDirectorySerializer
        if user.is_hr or user.is_admin:
            return EmployeeSerializer
        return EmployeeSelfSerializer

    def get_queryset(self):
        user = self.request.user
        qs = employee_list_qs(Employee.objects.filter(tenant=user.tenant))
        inactive = [Employee.Status.INACTIVE, Employee.Status.RESIGNED]

        if self.action == "list":
            return qs.exclude(status__in=inactive)
        if self.action == "retrieve":
            qs = qs.exclude(status__in=inactive)
            if user.is_hr or user.is_admin:
                return qs
            return qs
        if user.is_hr or user.is_admin:
            return qs
        profile = getattr(user, "employee_profile", None)
        if profile:
            return qs.filter(pk=profile.pk)
        return qs.none()

    @action(detail=False, methods=["get"])
    def me(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            return Response({"detail": "No employee profile linked."}, status=400)
        serializer_class = (
            EmployeeSerializer
            if (request.user.is_hr or request.user.is_admin)
            else EmployeeSelfSerializer
        )
        return Response(serializer_class(profile).data)

    @action(detail=False, methods=["get"], permission_classes=[IsAdminOrHR])
    def import_template(self, request):
        from apps.core.xlsx_io import xlsx_http_response

        return xlsx_http_response(template_xlsx(), "employee_import_template.xlsx")

    @action(detail=False, methods=["post"], permission_classes=[IsAdminOrHR])
    def import_csv(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "file required."}, status=400)
        try:
            result = import_employees_file(
                request.user.tenant,
                filename=upload.name,
                content=upload.read(),
            )
            return Response(result)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
