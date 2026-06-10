from django.contrib import admin

from apps.shifts.models import Shift, ShiftAssignment, ShiftRotationTemplate

admin.site.register(Shift)
admin.site.register(ShiftAssignment)
admin.site.register(ShiftRotationTemplate)
