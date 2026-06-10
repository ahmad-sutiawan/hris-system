from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.attendance.api import AttendanceRecordViewSet, DailyTimesheetViewSet
from apps.core.views import HealthCheckView
from apps.employees.api import EmployeeViewSet
from apps.leave.api import LeaveBalanceViewSet, LeaveRequestViewSet
from apps.payroll.api import PayrollRunViewSet, PayslipViewSet
from apps.shifts.api import ShiftAssignmentViewSet, ShiftViewSet

router = routers.DefaultRouter()
router.register("employees", EmployeeViewSet, basename="employee")
router.register("shifts", ShiftViewSet, basename="shift")
router.register("shift-assignments", ShiftAssignmentViewSet, basename="shift-assignment")
router.register("attendance", AttendanceRecordViewSet, basename="attendance")
router.register("timesheets", DailyTimesheetViewSet, basename="timesheet")
router.register("leave-requests", LeaveRequestViewSet, basename="leave-request")
router.register("leave-balances", LeaveBalanceViewSet, basename="leave-balance")
router.register("payroll-runs", PayrollRunViewSet, basename="payroll-run")
router.register("payslips", PayslipViewSet, basename="payslip")

urlpatterns = [
    path("", include(router.urls)),
    path("health/", HealthCheckView.as_view(), name="health"),
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
