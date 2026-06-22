"""Export rekap absensi — format Excel lengkap."""

from datetime import date, datetime, time
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.attendance.models import AttendanceCode, DailyTimesheet
from apps.attendance.services.export import (
    TIMESHEET_EXPORT_HEADERS,
    export_timesheets_xlsx,
    timesheet_to_row,
)
from apps.core.xlsx_io import read_xlsx_rows
from apps.core.models import Plant, Tenant
from apps.employees.models import Employee
from apps.organization.models import Department, JobPosition
from apps.shifts.models import Shift


class AttendanceExportFormatTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="export", name="Export Co")
        self.plant = Plant.objects.create(
            tenant=self.tenant,
            code="MPS",
            name="PT. Maju Perkasa Sentosa",
        )
        self.dept = Department.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="AM",
            name="Actors Management",
        )
        self.job = JobPosition.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            code="BD",
            title="Business Development",
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            job_position=self.job,
            employee_id="1004",
            full_name="Mario Marcello",
            join_date=date(2024, 1, 1),
        )
        self.shift = Shift.objects.create(
            tenant=self.tenant,
            code="OFF",
            name="Office",
            label="",
            scheduled_check_in=time(8, 0),
            scheduled_check_out=time(17, 0),
        )
        self.hadir = AttendanceCode.objects.create(
            tenant=self.tenant,
            code="H",
            label="Hadir",
        )
        tz = timezone.get_current_timezone()
        self.timesheet = DailyTimesheet.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee=self.employee,
            work_date=date(2024, 3, 1),
            shift=self.shift,
            shift_code="",
            shift_label="",
            scheduled_check_in=time(8, 0),
            scheduled_check_out=time(17, 0),
            attendance_code=self.hadir,
            time_off_code="",
            check_in=timezone.make_aware(datetime(2024, 3, 1, 8, 0), tz),
            check_out=timezone.make_aware(datetime(2024, 3, 1, 17, 0), tz),
            late_in_minutes=0,
            early_out_minutes=0,
            schedule_working_hours=Decimal("8.00"),
            actual_working_hours=Decimal("9.00"),
            paid_working_hours=Decimal("9.00"),
            ot_after_minutes=0,
            hourly_time_off_breakdown=[],
        )

    def test_export_headers_include_schedule_and_status_fields(self):
        self.assertIn("Schedule Check In", TIMESHEET_EXPORT_HEADERS)
        self.assertIn("Overtime Before", TIMESHEET_EXPORT_HEADERS)
        self.assertIn("Calculation Status", TIMESHEET_EXPORT_HEADERS)

    def test_export_row_matches_legacy_sample(self):
        row = timesheet_to_row(self.timesheet)
        self.assertEqual(row[0], "1004")
        self.assertEqual(row[1], "Mario Marcello")
        self.assertEqual(row[2], "PT. Maju Perkasa Sentosa")
        self.assertEqual(row[3], "MPS")
        self.assertEqual(row[4], "Actors Management")
        self.assertEqual(row[5], "Business Development")
        self.assertEqual(row[6], "2024-03-01")
        self.assertEqual(row[7], "Office")
        self.assertEqual(row[10], "08:00")
        self.assertEqual(row[11], "17:00")
        self.assertEqual(row[15], "08:00")
        self.assertEqual(row[16], "17:00")

    def test_export_xlsx_contains_headers(self):
        content = export_timesheets_xlsx([self.timesheet])
        headers, rows = read_xlsx_rows(content)
        self.assertEqual(headers, TIMESHEET_EXPORT_HEADERS)
        self.assertEqual(len(rows), 1)

    def test_hourly_time_off_breakdown_formatted(self):
        self.timesheet.hourly_time_off_breakdown = [
            {"start": "10:00", "finish": "12:00"},
        ]
        row = timesheet_to_row(self.timesheet)
        self.assertEqual(row[14], "10:00 - 12:00")
