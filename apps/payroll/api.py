from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.api_scoping import employee_scoped_queryset
from apps.core.permissions import IsAdminOrHR
from apps.core.viewsets import TenantScopedViewSet
from apps.payroll.access import restrict_payslip_visibility
from apps.payroll.models import PayrollRun, Payslip
from apps.payroll.serializers import PayrollRunSerializer, PayslipSerializer
from apps.core.xlsx_io import xlsx_http_response
from apps.payroll.services.bank_export import export_bank_xlsx
from apps.payroll.services.payslip_pdf import generate_payslip_pdf
from apps.payroll.services.compliance_export import export_bpjs_xlsx, export_pph21_xlsx
from apps.payroll.services.payroll_run import PayrollError, calculate_payroll_run, finalize_payroll_run
from apps.payroll.services.payroll_validation import PayrollValidationError, validate_payroll_against_xlsx


class PayrollRunViewSet(TenantScopedViewSet):
    queryset = PayrollRun.objects.select_related("plant")
    serializer_class = PayrollRunSerializer
    filterset_fields = ["plant", "status"]
    permission_classes = [IsAdminOrHR]

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    @action(detail=True, methods=["post"])
    def calculate(self, request, pk=None):
        run = self.get_object()
        try:
            calculate_payroll_run(run)
            return Response(PayrollRunSerializer(run).data)
        except PayrollError as exc:
            return Response({"detail": str(exc)}, status=400)

    @action(detail=True, methods=["post"])
    def finalize(self, request, pk=None):
        run = self.get_object()
        try:
            finalize_payroll_run(run)
            return Response(PayrollRunSerializer(run).data)
        except PayrollError as exc:
            return Response({"detail": str(exc)}, status=400)

    @action(detail=True, methods=["get"])
    def bank_export(self, request, pk=None):
        run = self.get_object()
        if run.status != PayrollRun.Status.FINALIZED:
            return Response({"detail": "Payroll must be finalized."}, status=400)
        return xlsx_http_response(export_bank_xlsx(run), f"bank_export_{run.plant.code}.xlsx")

    @action(detail=True, methods=["get"])
    def bpjs_export(self, request, pk=None):
        run = self.get_object()
        return xlsx_http_response(export_bpjs_xlsx(run), f"bpjs_{run.plant.code}_{run.period_end}.xlsx")

    @action(detail=True, methods=["get"])
    def pph21_export(self, request, pk=None):
        run = self.get_object()
        return xlsx_http_response(export_pph21_xlsx(run), f"pph21_{run.plant.code}_{run.period_end}.xlsx")

    @action(detail=True, methods=["post"])
    def validate_csv(self, request, pk=None):
        run = self.get_object()
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "file required."}, status=400)
        try:
            result = validate_payroll_against_xlsx(run, upload.read())
            return Response(result)
        except PayrollValidationError as exc:
            return Response({"detail": str(exc)}, status=400)


class PayslipViewSet(TenantScopedViewSet):
    queryset = Payslip.objects.select_related("employee", "payroll_run")
    serializer_class = PayslipSerializer
    filterset_fields = ["payroll_run", "employee"]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        qs = employee_scoped_queryset(self.request.user, qs)
        return restrict_payslip_visibility(qs, self.request.user)

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        payslip = self.get_object()
        profile = getattr(request.user, "employee_profile", None)
        if not (request.user.is_hr or request.user.is_admin):
            if not profile or profile.id != payslip.employee_id:
                return Response({"detail": "Forbidden."}, status=403)
            if payslip.payroll_run.status != PayrollRun.Status.FINALIZED:
                return Response({"detail": "Slip gaji belum tersedia."}, status=403)

        if payslip.pdf_file:
            response = HttpResponse(payslip.pdf_file.read(), content_type="application/pdf")
        else:
            response = HttpResponse(generate_payslip_pdf(payslip), content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="slip_{payslip.employee.employee_id}.pdf"'
        )
        return response
