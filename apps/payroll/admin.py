from django.contrib import admin

from apps.payroll.models import (
    PayrollRun,
    Payslip,
    Pph21TerBracket,
    Pph21TerCategory,
    Pph21TerPtkpMapping,
    SalaryComponent,
    THRRun,
)

admin.site.register(SalaryComponent)
admin.site.register(PayrollRun)
admin.site.register(Payslip)
admin.site.register(THRRun)
admin.site.register(Pph21TerCategory)
admin.site.register(Pph21TerPtkpMapping)
admin.site.register(Pph21TerBracket)
