from rest_framework import serializers

from apps.payroll.models import PayrollRun, Payslip


class PayrollRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollRun
        fields = [
            "id",
            "plant",
            "period_start",
            "period_end",
            "status",
            "finalized_at",
            "notes",
            "created_at",
        ]
        read_only_fields = ["status", "finalized_at", "created_at"]


class PayslipSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_code = serializers.CharField(source="employee.employee_id", read_only=True)

    class Meta:
        model = Payslip
        fields = [
            "id",
            "payroll_run",
            "employee",
            "employee_code",
            "employee_name",
            "gross_amount",
            "deduction_amount",
            "net_amount",
            "earnings_breakdown",
            "deductions_breakdown",
            "verification_hash",
        ]
