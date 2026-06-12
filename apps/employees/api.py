from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.api_scoping import employee_scoped_queryset
from apps.core.permissions import IsAdminOrHR
from apps.core.querysets import employee_list_qs
from apps.core.viewsets import TenantScopedViewSet
from apps.employees.models import Employee
from apps.employees.serializers import EmployeeSerializer
from apps.employees.services.import_csv import import_employees_csv, template_csv


class EmployeeViewSet(TenantScopedViewSet):
    queryset = employee_list_qs(Employee.objects.all())
    serializer_class = EmployeeSerializer
    search_fields = ["employee_id", "full_name", "nik", "email"]
    filterset_fields = ["plant", "department", "status"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
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
        return Response(EmployeeSerializer(profile).data)

    @action(detail=False, methods=["get"], permission_classes=[IsAdminOrHR])
    def import_template(self, request):
        from django.http import HttpResponse

        response = HttpResponse(template_csv(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="employee_import_template.csv"'
        return response

    @action(detail=False, methods=["post"], permission_classes=[IsAdminOrHR])
    def import_csv(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "file required."}, status=400)
        content = upload.read().decode("utf-8-sig")
        try:
            result = import_employees_csv(request.user.tenant, content)
            return Response(result)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
