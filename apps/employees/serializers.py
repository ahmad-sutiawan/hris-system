from rest_framework import serializers

from apps.employees.models import Employee


class EmployeeSerializer(serializers.ModelSerializer):
    plant_code = serializers.CharField(source="plant.code", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    job_title = serializers.CharField(source="job_position.title", read_only=True)
    grade_code = serializers.CharField(source="employee_grade.code", read_only=True)
    grade_name = serializers.CharField(source="employee_grade.name", read_only=True)
    daily_wage = serializers.DecimalField(
        source="employee_grade.daily_wage",
        max_digits=14,
        decimal_places=2,
        read_only=True,
    )

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
            "employee_grade",
            "grade_code",
            "grade_name",
            "daily_wage",
            "manager",
            "status",
            "join_date",
            "salary_scheme",
            "base_salary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
