from django.contrib import admin

from apps.payroll.models import PayrollRun, Payslip, SalaryComponent, THRRun

admin.site.register(SalaryComponent)
admin.site.register(PayrollRun)
admin.site.register(Payslip)
admin.site.register(THRRun)
