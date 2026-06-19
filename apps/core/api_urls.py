from django.urls import include, path
from rest_framework import routers

from apps.attendance.api import AttendanceRecordViewSet, DailyTimesheetViewSet
from apps.attendance.api_overtime import OvertimeRequestViewSet, OvertimeTypeViewSet
from apps.core.api_announcements import AnnouncementViewSet
from apps.core.api_auth import (
    AuthLogoutView,
    AuthMeView,
    ThrottledTokenObtainPairView,
    ThrottledTokenRefreshView,
)
from apps.core.api_mobile import MobileDashboardView, MobileEmployeeFiltersView, MobileProfileView
from apps.core.api_media import MediaFileView
from apps.core.api_views import AuditLogViewSet, NotificationViewSet
from apps.core.views import HealthCheckView
from apps.employees.api import EmployeeViewSet
from apps.leave.api import LeaveBalanceViewSet, LeaveRequestViewSet
from apps.leave.api_types import LeaveTypeViewSet
from apps.payroll.api import PayrollRunViewSet, PayslipViewSet
from apps.shifts.api import ShiftAssignmentViewSet, ShiftViewSet

router = routers.DefaultRouter()
router.register("audit-logs", AuditLogViewSet, basename="audit-log")
router.register("announcements", AnnouncementViewSet, basename="announcement")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("employees", EmployeeViewSet, basename="employee")
router.register("shifts", ShiftViewSet, basename="shift")
router.register("shift-assignments", ShiftAssignmentViewSet, basename="shift-assignment")
router.register("attendance", AttendanceRecordViewSet, basename="attendance")
router.register("timesheets", DailyTimesheetViewSet, basename="timesheet")
router.register("leave-types", LeaveTypeViewSet, basename="leave-type")
router.register("leave-requests", LeaveRequestViewSet, basename="leave-request")
router.register("leave-balances", LeaveBalanceViewSet, basename="leave-balance")
router.register("overtime-types", OvertimeTypeViewSet, basename="overtime-type")
router.register("overtime-requests", OvertimeRequestViewSet, basename="overtime-request")
router.register("payroll-runs", PayrollRunViewSet, basename="payroll-run")
router.register("payslips", PayslipViewSet, basename="payslip")

urlpatterns = [
    path("", include(router.urls)),
    path("health/", HealthCheckView.as_view(), name="health"),
    path("auth/me/", AuthMeView.as_view(), name="auth_me"),
    path("auth/token/", ThrottledTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", ThrottledTokenRefreshView.as_view(), name="token_refresh"),
    path("auth/logout/", AuthLogoutView.as_view(), name="token_logout"),
    path("mobile/dashboard/", MobileDashboardView.as_view(), name="mobile_dashboard"),
    path("mobile/profile/", MobileProfileView.as_view(), name="mobile_profile"),
    path("mobile/employees/filters/", MobileEmployeeFiltersView.as_view(), name="mobile_employee_filters"),
    path("media/<path:path>", MediaFileView.as_view(), name="api_media"),
]
