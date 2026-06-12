from django.contrib import admin

from apps.organization.models import Department, EmployeeGrade, JobPosition, LegalEntity

admin.site.register(LegalEntity)
admin.site.register(Department)
admin.site.register(JobPosition)
admin.site.register(EmployeeGrade)
