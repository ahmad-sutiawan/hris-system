from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from apps.web import views

app_name = "web"

urlpatterns = [
    path("login/", LoginView.as_view(template_name="web/login.html"), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("punch/", views.punch_action, name="punch"),
    path("employees/", views.employee_list, name="employee_list"),
    path("employees/new/", views.employee_create, name="employee_create"),
    path("employees/import/", views.employee_import, name="employee_import"),
    path("employees/import/template/", views.employee_import_template, name="employee_import_template"),
    path("shifts/assign/", views.shift_assign, name="shift_assign"),
    path("attendance/", views.attendance_list, name="attendance_list"),
    path("attendance/export/", views.attendance_export, name="attendance_export"),
    path("leave/", views.leave_list, name="leave_list"),
    path("leave/new/", views.leave_create, name="leave_create"),
    path("leave/<int:pk>/approve/", views.leave_approve, name="leave_approve"),
    path("leave/<int:pk>/reject/", views.leave_reject, name="leave_reject"),
    path("payroll/", views.payroll_list, name="payroll_list"),
    path("payroll/new/", views.payroll_create, name="payroll_create"),
    path("payroll/<int:pk>/", views.payroll_detail, name="payroll_detail"),
    path("payroll/<int:pk>/calculate/", views.payroll_calculate, name="payroll_calculate"),
    path("payroll/<int:pk>/finalize/", views.payroll_finalize, name="payroll_finalize"),
    path("payroll/<int:pk>/bank-export/", views.payroll_bank_export, name="payroll_bank_export"),
    path("payslips/", views.payslip_list, name="payslip_list"),
    path("payslips/<int:pk>/download/", views.payslip_download, name="payslip_download"),
    path("notifications/", views.notification_list, name="notification_list"),
    path("notifications/<int:pk>/read/", views.notification_mark_read, name="notification_mark_read"),
    path("notifications/read-all/", views.notification_mark_all_read, name="notification_mark_all_read"),
    path("audit/", views.audit_log_list, name="audit_log_list"),
]
