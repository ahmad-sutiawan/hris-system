from django.contrib import admin

from apps.leave.models import LeaveBalance, LeaveHourlySegment, LeaveRequest, LeaveType

admin.site.register(LeaveType)
admin.site.register(LeaveBalance)
admin.site.register(LeaveRequest)
admin.site.register(LeaveHourlySegment)
