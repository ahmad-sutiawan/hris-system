from rest_framework import serializers

from apps.employees.models import Employee
from apps.payroll.services.calculator import effective_daily_wage, hourly_rate


class EmployeeSerializer(serializers.ModelSerializer):
    plant_code = serializers.CharField(source="plant.code", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    job_title = serializers.CharField(source="job_position.title", read_only=True)
    grade_code = serializers.CharField(source="employee_grade.code", read_only=True)
    grade_name = serializers.CharField(source="employee_grade.name", read_only=True)
    grade_daily_wage = serializers.DecimalField(
        source="employee_grade.daily_wage",
        max_digits=14,
        decimal_places=2,
        read_only=True,
    )
    effective_daily_wage = serializers.SerializerMethodField()
    effective_hourly_wage = serializers.SerializerMethodField()
    manager_name = serializers.CharField(source="manager.full_name", read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "employee_id",
            "full_name",
            "nik",
            "email",
            "phone",
            "plant",
            "plant_code",
            "legal_entity",
            "department",
            "department_name",
            "job_position",
            "job_title",
            "employee_grade",
            "grade_code",
            "grade_name",
            "grade_daily_wage",
            "effective_daily_wage",
            "effective_hourly_wage",
            "manager",
            "manager_name",
            "status",
            "join_date",
            "contract_end_date",
            "resign_date",
            "salary_scheme",
            "base_salary",
            "allowance_transport",
            "allowance_meal",
            "allowance_position",
            "bank_name",
            "bank_account_number",
            "bank_account_name",
            "npwp",
            "tax_status",
            "bpjs_kesehatan_number",
            "bpjs_ketenagakerjaan_number",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_effective_daily_wage(self, obj) -> str:
        return str(effective_daily_wage(obj))

    def get_effective_hourly_wage(self, obj) -> str:
        return str(hourly_rate(obj))
