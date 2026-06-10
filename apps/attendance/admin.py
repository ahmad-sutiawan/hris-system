from django.contrib import admin

from apps.attendance.models import AttendanceCode, AttendanceRecord, DailyTimesheet

admin.site.register(AttendanceCode)
admin.site.register(AttendanceRecord)
admin.site.register(DailyTimesheet)
