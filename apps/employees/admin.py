from django.contrib import admin

from apps.employees.models import Employee, EmployeeDocument


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        "employee_id",
        "full_name",
        "plant",
        "employee_grade",
        "salary_scheme",
        "status",
    ]
    list_filter = ["plant", "status", "salary_scheme", "employee_grade"]
    search_fields = ["employee_id", "full_name", "nik", "email"]
    list_select_related = ["plant", "employee_grade", "department", "job_position"]
    raw_id_fields = ["manager", "user"]


admin.site.register(EmployeeDocument)
