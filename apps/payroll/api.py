from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.viewsets import TenantScopedViewSet
from apps.payroll.models import PayrollRun, Payslip
from apps.payroll.serializers import PayrollRunSerializer, PayslipSerializer
from apps.payroll.services.bank_export import export_bank_csv
from apps.payroll.services.payslip_pdf import generate_payslip_pdf
from apps.payroll.services.compliance_export import export_bpjs_csv, export_pph21_csv
from apps.payroll.services.payroll_run import PayrollError, calculate_payroll_run, finalize_payroll_run
from apps.payroll.services.payroll_validation import PayrollValidationError, validate_payroll_against_csv


class PayrollRunViewSet(TenantScopedViewSet):
    queryset = PayrollRun.objects.select_related("plant")
    serializer_class = PayrollRunSerializer
    filterset_fields = ["plant", "status"]

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
        content = export_bank_csv(run)
        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="bank_export_{run.plant.code}.csv"'
        return response

    @action(detail=True, methods=["get"])
    def bpjs_export(self, request, pk=None):
        run = self.get_object()
        content = export_bpjs_csv(run)
        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="bpjs_{run.plant.code}_{run.period_end}.csv"'
        return response

    @action(detail=True, methods=["get"])
    def pph21_export(self, request, pk=None):
        run = self.get_object()
        content = export_pph21_csv(run)
        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="pph21_{run.plant.code}_{run.period_end}.csv"'
        return response

    @action(detail=True, methods=["post"])
    def validate_csv(self, request, pk=None):
        run = self.get_object()
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "file required."}, status=400)
        try:
            result = validate_payroll_against_csv(run, upload.read().decode("utf-8-sig"))
            return Response(result)
        except PayrollValidationError as exc:
            return Response({"detail": str(exc)}, status=400)


class PayslipViewSet(TenantScopedViewSet):
    queryset = Payslip.objects.select_related("employee", "payroll_run")
    serializer_class = PayslipSerializer
    filterset_fields = ["payroll_run", "employee"]

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        payslip = self.get_object()
        profile = getattr(request.user, "employee_profile", None)
        if not (request.user.is_hr or request.user.is_admin):
            if not profile or profile.id != payslip.employee_id:
                return Response({"detail": "Forbidden."}, status=403)

        if payslip.pdf_file:
            response = HttpResponse(payslip.pdf_file.read(), content_type="application/pdf")
        else:
            response = HttpResponse(generate_payslip_pdf(payslip), content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="slip_{payslip.employee.employee_id}.pdf"'
        )
        return response
