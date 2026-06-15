"""Filtered querysets for web list views — shared between page render and CSV export."""

from django.db.models import Q
from django.utils import timezone

from apps.attendance.models import AttendanceRecord, DailyTimesheet, OvertimeRequest
from apps.core.listing import (
    ListFilters,
    apply_date_field_range,
    apply_datetime_range,
    apply_period_overlap,
)
from apps.core.models import AuditLog, Notification, User
from apps.core.querysets import audit_log_list_qs, employee_list_qs, timesheet_list_qs
from apps.employees.models import Employee
from apps.leave.models import LeaveRequest
from apps.payroll.models import PayrollRun, Payslip
from apps.shifts.models import ShiftAssignment


def _employee_profile(user):
    return getattr(user, "employee_profile", None)


def _plant_scope(user, qs, *, plant_path: str = "plant"):
    if user.plant_id and not user.is_admin:
        return qs.filter(**{f"{plant_path}": user.plant})
    return qs


def employee_list_queryset(user: User, filters: ListFilters):
    qs = employee_list_qs(Employee.objects.filter(tenant=user.tenant))
    qs = _plant_scope(user, qs)
    if filters.q:
        text = filters.q
        search = (
            Q(employee_id__icontains=text)
            | Q(full_name__icontains=text)
            | Q(nik__icontains=text)
            | Q(email__icontains=text)
            | Q(phone__icontains=text)
            | Q(npwp__icontains=text)
            | Q(tax_status__icontains=text)
            | Q(bank_name__icontains=text)
            | Q(bank_account_number__icontains=text)
            | Q(bank_account_name__icontains=text)
            | Q(status__icontains=text)
            | Q(salary_scheme__icontains=text)
            | Q(bpjs_kesehatan_number__icontains=text)
            | Q(bpjs_ketenagakerjaan_number__icontains=text)
            | Q(plant__code__icontains=text)
            | Q(plant__name__icontains=text)
            | Q(department__name__icontains=text)
            | Q(department__code__icontains=text)
            | Q(job_position__title__icontains=text)
            | Q(job_position__code__icontains=text)
            | Q(manager__full_name__icontains=text)
            | Q(manager__employee_id__icontains=text)
            | Q(user__username__icontains=text)
            | Q(employee_grade__code__icontains=text)
            | Q(employee_grade__name__icontains=text)
        )
        qs = qs.filter(search)
    qs = apply_date_field_range(
        qs, date_from=filters.date_from, date_to=filters.date_to, field_name="join_date"
    )
    return qs.order_by("full_name")


def shift_assignment_queryset(user: User, filters: ListFilters):
    qs = ShiftAssignment.objects.filter(tenant=user.tenant).select_related("employee", "shift")
    qs = _plant_scope(user, qs, plant_path="employee__plant")
    if filters.q:
        qs = qs.filter(
            Q(employee__full_name__icontains=filters.q)
            | Q(employee__employee_id__icontains=filters.q)
            | Q(shift__code__icontains=filters.q)
            | Q(shift__name__icontains=filters.q)
        )
    qs = apply_date_field_range(
        qs, date_from=filters.date_from, date_to=filters.date_to, field_name="work_date"
    )
    return qs.order_by("-work_date", "employee__full_name")


def attendance_list_queryset(user: User, filters: ListFilters):
    qs = timesheet_list_qs(DailyTimesheet.objects.filter(tenant=user.tenant))
    profile = _employee_profile(user)
    if profile and not user.is_hr:
        qs = qs.filter(employee=profile)
    if filters.q:
        qs = qs.filter(
            Q(employee__employee_id__icontains=filters.q)
            | Q(employee__full_name__icontains=filters.q)
            | Q(shift_code__icontains=filters.q)
            | Q(attendance_code__code__icontains=filters.q)
        )
    qs = apply_date_field_range(
        qs, date_from=filters.date_from, date_to=filters.date_to, field_name="work_date"
    )
    return qs.order_by("-work_date", "employee__full_name")


def leave_list_queryset(user: User, filters: ListFilters):
    qs = LeaveRequest.objects.filter(tenant=user.tenant).select_related("employee", "leave_type")
    profile = _employee_profile(user)
    if profile and not user.is_hr:
        qs = qs.filter(employee=profile)
    elif user.plant_id and not user.is_admin:
        qs = qs.filter(employee__plant=user.plant)
    if filters.q:
        qs = qs.filter(
            Q(employee__full_name__icontains=filters.q)
            | Q(employee__employee_id__icontains=filters.q)
            | Q(leave_type__code__icontains=filters.q)
            | Q(leave_type__name__icontains=filters.q)
            | Q(status__icontains=filters.q)
            | Q(reason__icontains=filters.q)
        )
    qs = apply_period_overlap(
        qs,
        date_from=filters.date_from,
        date_to=filters.date_to,
        start_field="start_date",
        end_field="end_date",
    )
    return qs.order_by("-created_at")


def overtime_list_queryset(user: User, filters: ListFilters):
    qs = OvertimeRequest.objects.filter(tenant=user.tenant).select_related(
        "employee", "approver", "overtime_type"
    )
    profile = _employee_profile(user)
    if profile and not user.is_hr:
        qs = qs.filter(employee=profile)
    elif user.plant_id and not user.is_admin:
        qs = qs.filter(employee__plant=user.plant)
    if filters.q:
        qs = qs.filter(
            Q(employee__full_name__icontains=filters.q)
            | Q(employee__employee_id__icontains=filters.q)
            | Q(status__icontains=filters.q)
            | Q(reason__icontains=filters.q)
        )
    qs = apply_date_field_range(
        qs, date_from=filters.date_from, date_to=filters.date_to, field_name="work_date"
    )
    return qs.order_by("-created_at")


def payroll_list_queryset(user: User, filters: ListFilters):
    qs = PayrollRun.objects.filter(tenant=user.tenant).select_related("plant")
    if user.plant_id and not user.is_admin:
        qs = qs.filter(plant=user.plant)
    if filters.q:
        qs = qs.filter(
            Q(plant__code__icontains=filters.q)
            | Q(plant__name__icontains=filters.q)
            | Q(status__icontains=filters.q)
            | Q(notes__icontains=filters.q)
        )
    qs = apply_period_overlap(
        qs,
        date_from=filters.date_from,
        date_to=filters.date_to,
        start_field="period_start",
        end_field="period_end",
    )
    return qs.order_by("-period_end")


def payslip_list_queryset(user: User, filters: ListFilters):
    profile = _employee_profile(user)
    if user.is_hr or user.is_admin:
        qs = Payslip.objects.filter(tenant=user.tenant).select_related(
            "employee", "payroll_run", "payroll_run__plant"
        )
        if user.plant_id and not user.is_admin:
            qs = qs.filter(payroll_run__plant=user.plant)
    elif profile:
        qs = Payslip.objects.filter(employee=profile).select_related(
            "payroll_run", "payroll_run__plant"
        )
    else:
        return Payslip.objects.none()
    if filters.q:
        qs = qs.filter(
            Q(employee__full_name__icontains=filters.q)
            | Q(employee__employee_id__icontains=filters.q)
            | Q(verification_hash__icontains=filters.q)
            | Q(payroll_run__plant__code__icontains=filters.q)
        )
    qs = apply_period_overlap(
        qs,
        date_from=filters.date_from,
        date_to=filters.date_to,
        start_field="payroll_run__period_start",
        end_field="payroll_run__period_end",
    )
    return qs.order_by("-payroll_run__period_end", "employee__full_name")


def notification_list_queryset(user: User, filters: ListFilters):
    qs = Notification.objects.filter(user=user)
    if filters.q:
        qs = qs.filter(
            Q(title__icontains=filters.q)
            | Q(message__icontains=filters.q)
            | Q(category__icontains=filters.q)
        )
    qs = apply_datetime_range(
        qs, date_from=filters.date_from, date_to=filters.date_to, field_name="created_at"
    )
    return qs.order_by("-created_at")


def audit_log_queryset(user: User, filters: ListFilters, *, default_days: int = 90):
    qs = audit_log_list_qs(
        AuditLog.objects.filter(tenant=user.tenant),
        include_changes=True,
    )
    if filters.date_from or filters.date_to:
        qs = apply_datetime_range(
            qs, date_from=filters.date_from, date_to=filters.date_to, field_name="created_at"
        )
    else:
        qs = qs.filter(created_at__gte=timezone.now() - timezone.timedelta(days=default_days))
    return qs.order_by("-created_at")


def payroll_detail_payslip_queryset(run, filters: ListFilters):
    qs = Payslip.objects.filter(payroll_run=run).select_related("employee")
    if filters.q:
        qs = qs.filter(
            Q(employee__full_name__icontains=filters.q)
            | Q(employee__employee_id__icontains=filters.q)
        )
    return qs.order_by("employee__full_name")


def attach_attendance_records(timesheets, tenant):
    record_map = {}
    if not timesheets:
        return record_map
    records = AttendanceRecord.objects.filter(
        tenant=tenant,
        employee_id__in={row.employee_id for row in timesheets},
        work_date__in={row.work_date for row in timesheets},
    )
    record_map = {(r.employee_id, r.work_date): r for r in records}
    for row in timesheets:
        row.punch_record = record_map.get((row.employee_id, row.work_date))
    return record_map
