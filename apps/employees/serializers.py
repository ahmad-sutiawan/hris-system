from rest_framework import serializers

from apps.employees.models import Employee


class EmployeeSerializer(serializers.ModelSerializer):
    plant_code = serializers.CharField(source="plant.code", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    job_title = serializers.CharField(source="job_position.title", read_only=True)

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
            "department",
            "department_name",
            "job_position",
            "job_title",
            "manager",
            "status",
            "join_date",
            "salary_scheme",
            "base_salary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
