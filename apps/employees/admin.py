from django.contrib import admin

from apps.employees.models import Employee, EmployeeDocument

admin.site.register(Employee)
admin.site.register(EmployeeDocument)
