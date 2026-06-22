from rest_framework import serializers

from apps.employees.models import Employee
from apps.employees.services.photo import employee_photo_url
from apps.payroll.services.calculator import effective_daily_wage, hourly_rate


class EmployeePhotoUrlMixin:
    photo_url = serializers.SerializerMethodField()

    def get_photo_url(self, obj):
        return employee_photo_url(obj, request=self.context.get("request"))


class EmployeeDirectorySerializer(EmployeePhotoUrlMixin, serializers.ModelSerializer):
    """Safe employee list for mobile directory — no compensation fields."""

    plant_code = serializers.CharField(source="plant.code", read_only=True)
    plant_name = serializers.CharField(source="plant.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    job_title = serializers.CharField(source="job_position.title", read_only=True)
    manager_name = serializers.CharField(source="manager.full_name", read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "employee_id",
            "full_name",
            "email",
            "phone",
            "plant",
            "plant_code",
            "plant_name",
            "department",
            "department_name",
            "job_position",
            "job_title",
            "manager",
            "manager_name",
            "status",
            "join_date",
            "photo_url",
        ]
        read_only_fields = fields


class EmployeeSerializer(EmployeePhotoUrlMixin, serializers.ModelSerializer):
    """Full employee record — HR/Admin only."""
    plant_code = serializers.CharField(source="plant.code", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    job_title = serializers.CharField(source="job_position.title", read_only=True)
    effective_daily_wage = serializers.SerializerMethodField()
    effective_hourly_wage = serializers.SerializerMethodField()
    manager_name = serializers.CharField(source="manager.full_name", read_only=True)
    legal_entity_name = serializers.CharField(source="legal_entity.name", read_only=True)

    default_shift_code = serializers.CharField(source="default_shift.code", read_only=True)
    default_shift_name = serializers.CharField(source="default_shift.name", read_only=True)

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
            "legal_entity_name",
            "department",
            "department_name",
            "job_position",
            "job_title",
            "default_shift",
            "default_shift_code",
            "default_shift_name",
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
            "pph21_deduct",
            "bpjs_kesehatan_number",
            "bpjs_ketenagakerjaan_number",
            "photo_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "created_at",
            "updated_at",
            "legal_entity",
            "legal_entity_name",
            "default_shift",
            "default_shift_code",
            "default_shift_name",
        ]

    def get_effective_daily_wage(self, obj) -> str:
        return str(effective_daily_wage(obj))

    def get_effective_hourly_wage(self, obj) -> str:
        return str(hourly_rate(obj))


class EmployeeSelfSerializer(EmployeePhotoUrlMixin, serializers.ModelSerializer):
    """Read-only profile for the logged-in employee (no compensation/PII edits)."""

    plant_code = serializers.CharField(source="plant.code", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    job_title = serializers.CharField(source="job_position.title", read_only=True)
    manager_name = serializers.CharField(source="manager.full_name", read_only=True)
    default_shift_code = serializers.CharField(source="default_shift.code", read_only=True)
    default_shift_name = serializers.CharField(source="default_shift.name", read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "employee_id",
            "full_name",
            "email",
            "phone",
            "address",
            "plant",
            "plant_code",
            "department",
            "department_name",
            "job_position",
            "job_title",
            "default_shift_code",
            "default_shift_name",
            "manager",
            "manager_name",
            "status",
            "join_date",
            "gender",
            "marital_status",
            "birth_place",
            "birth_date",
            "mother_name",
            "photo_url",
        ]
        read_only_fields = fields
