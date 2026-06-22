"""Batch-load attendance records + punches for timesheet rows (avoids N+1)."""

from django.db.models import Prefetch

from apps.attendance.models import AttendancePunch, AttendanceRecord


def attendance_record_map(timesheets, tenant) -> dict:
    """Return {(employee_id, work_date): AttendanceRecord} with sorted punches prefetched."""
    if not timesheets:
        return {}
    punch_qs = AttendancePunch.objects.order_by("punched_at", "pk")
    records = AttendanceRecord.objects.filter(
        tenant=tenant,
        employee_id__in={row.employee_id for row in timesheets},
        work_date__in={row.work_date for row in timesheets},
    ).prefetch_related(Prefetch("punches", queryset=punch_qs, to_attr="_prefetched_punches"))
    return {(record.employee_id, record.work_date): record for record in records}
