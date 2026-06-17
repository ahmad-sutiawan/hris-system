"""Tahap 2 — cross-day shift, holiday punch, retention."""

from datetime import date, datetime, time, timedelta
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.attendance.models import AttendanceCode, AttendanceRecord, DailyTimesheet
from apps.attendance.services.punch import clock_in, clock_out
from apps.attendance.services.punch_work_date import resolve_punch_work_date
from apps.attendance.services.retention import purge_attendance_data
from apps.attendance.services.timesheet import recalculate_daily_timesheet
from apps.core.models import HolidayCalendar, Plant, Tenant
from apps.employees.models import Employee
from apps.shifts.models import Shift, ShiftAssignment


def _photo():
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (400, 400), color=(200, 180, 160)).save(buf, format="JPEG")
    return SimpleUploadedFile("selfie.jpg", buf.getvalue(), content_type="image/jpeg")


@override_settings(ALLOWED_HOSTS=["testserver"])
class CrossDayShiftTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="t2", name="T2 Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="E001",
            full_name="Night Worker",
            join_date=date(2024, 1, 1),
        )
        self.night_shift = Shift.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="MALAM",
            name="Shift Malam",
            scheduled_check_in=time(22, 0),
            scheduled_check_out=time(6, 0),
            cross_day=True,
        )
        AttendanceCode.objects.create(tenant=self.tenant, code="H", label="Hadir")
        self.work_date = date(2026, 6, 1)
        ShiftAssignment.objects.create(
            tenant=self.tenant,
            employee=self.employee,
            shift=self.night_shift,
            work_date=self.work_date,
            scheduled_check_in=time(22, 0),
            scheduled_check_out=time(6, 0),
        )

    def test_clock_out_next_morning_same_work_date(self):
        tz = timezone.get_current_timezone()
        ci = timezone.make_aware(datetime(2026, 6, 1, 22, 0), tz)
        co = timezone.make_aware(datetime(2026, 6, 2, 6, 0), tz)

        clock_in(self.employee, when=ci, photo=_photo())
        record = clock_out(self.employee, when=co, photo=_photo())

        self.assertEqual(record.work_date, self.work_date)
        ts = DailyTimesheet.objects.get(employee=self.employee, work_date=self.work_date)
        self.assertIsNotNone(ts.check_in)
        self.assertIsNotNone(ts.check_out)

    def test_resolve_work_date_morning_tail_without_prior_check_in(self):
        tz = timezone.get_current_timezone()
        when = timezone.make_aware(datetime(2026, 6, 2, 0, 30), tz)
        resolved = resolve_punch_work_date(self.employee, when, is_clock_out=False)
        self.assertEqual(resolved, self.work_date)


@override_settings(ALLOWED_HOSTS=["testserver"])
class HolidayPunchTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="hol", name="Hol Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="E002",
            full_name="Holiday Worker",
            join_date=date(2024, 1, 1),
        )
        AttendanceCode.objects.create(tenant=self.tenant, code="H", label="Hadir")
        self.holiday = date(2026, 6, 1)
        HolidayCalendar.objects.create(
            tenant=self.tenant,
            name="Libur Demo",
            holiday_date=self.holiday,
            holiday_type=HolidayCalendar.HolidayType.NATIONAL,
        )

    def test_punch_on_holiday_marked_libur(self):
        tz = timezone.get_current_timezone()
        ci = timezone.make_aware(datetime(2026, 6, 1, 8, 0), tz)
        co = timezone.make_aware(datetime(2026, 6, 1, 17, 0), tz)
        clock_in(self.employee, when=ci, photo=_photo())
        clock_out(self.employee, when=co, photo=_photo())

        ts = DailyTimesheet.objects.get(employee=self.employee, work_date=self.holiday)
        self.assertEqual(ts.time_off_code, "LIBUR")
        self.assertEqual(ts.attendance_code.code, "H")


@override_settings(ALLOWED_HOSTS=["testserver"])
class RetentionTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="ret", name="Ret Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="E003",
            full_name="Old Worker",
            join_date=date(2020, 1, 1),
        )

    def test_purge_dry_run_counts_old_records(self):
        old_date = timezone.localdate() - timedelta(days=200)
        AttendanceRecord.objects.create(
            tenant=self.tenant,
            employee=self.employee,
            plant=self.plant,
            work_date=old_date,
        )
        DailyTimesheet.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee=self.employee,
            work_date=old_date,
        )
        stats = purge_attendance_data(tenant=self.tenant, dry_run=True)
        self.assertGreaterEqual(stats["records_to_delete"], 1)
        self.assertGreaterEqual(stats["timesheets_to_delete"], 1)
        self.assertTrue(stats["dry_run"])
        self.assertEqual(AttendanceRecord.objects.count(), 1)
