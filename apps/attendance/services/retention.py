"""Attendance data retention — 6 months records, 1 month photos."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.attendance.models import AttendanceRecord, DailyTimesheet


def purge_attendance_data(*, tenant=None, dry_run=True) -> dict:
    today = timezone.localdate()
    record_cutoff = today - timedelta(days=180)
    photo_cutoff = today - timedelta(days=30)

    records = AttendanceRecord.objects.filter(work_date__lt=record_cutoff)
    timesheets = DailyTimesheet.objects.filter(work_date__lt=record_cutoff)
    if tenant:
        records = records.filter(tenant=tenant)
        timesheets = timesheets.filter(tenant=tenant)

    photo_qs = AttendanceRecord.objects.filter(work_date__lt=photo_cutoff)
    if tenant:
        photo_qs = photo_qs.filter(tenant=tenant)

    photos_cleared = 0
    for rec in photo_qs.iterator():
        changed = False
        for field in ("check_in_photo", "check_out_photo"):
            f = getattr(rec, field)
            if f:
                if not dry_run:
                    f.delete(save=False)
                    setattr(rec, field, "")
                changed = True
                photos_cleared += 1
        if changed and not dry_run:
            rec.save(update_fields=["check_in_photo", "check_out_photo", "updated_at"])

    stats = {
        "records_to_delete": records.count(),
        "timesheets_to_delete": timesheets.count(),
        "photos_cleared": photos_cleared,
        "dry_run": dry_run,
    }

    if not dry_run:
        records.delete()
        timesheets.delete()

    return stats
