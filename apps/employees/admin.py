from django.contrib import admin

from apps.employees.models import Employee, EmployeeDocument


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        "employee_id",
        "full_name",
        "plant",
        "salary_scheme",
        "tax_status",
        "status",
    ]
    list_filter = ["plant", "status", "salary_scheme"]
    search_fields = ["employee_id", "full_name", "nik", "email", "tax_status"]
    list_select_related = [
        "plant",
        "legal_entity",
        "department",
        "job_position",
        "default_shift",
    ]
    raw_id_fields = ["manager", "user", "legal_entity"]


admin.site.register(EmployeeDocument)
