"""Tahap 1 alignment tests — OT policy, export, attendance correction."""

from datetime import date, time

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.attendance.models import AttendanceCode, AttendanceRecord, DailyTimesheet
from apps.attendance.services.correction import apply_attendance_correction
from apps.attendance.services.policy import ot_before_overtime_enabled
from apps.attendance.services.timesheet import recalculate_daily_timesheet
from apps.core.models import AuditLog, Plant, Tenant, User
from apps.employees.models import Employee
from apps.shifts.models import Shift


@override_settings(ALLOWED_HOSTS=["testserver"])
class Tahap1PolicyTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="tahap1", name="Tahap1 Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.admin = User.objects.create_user(
            username="tahap1admin",
            password="TestPassword123!",
            tenant=self.tenant,
            role=User.Role.ADMIN,
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="E001",
            full_name="Budi Santoso",
            join_date=date(2024, 1, 1),
        )
        self.shift = Shift.objects.create(
            tenant=self.tenant,
            code="S1",
            name="Shift 1",
            scheduled_check_in=time(8, 0),
            scheduled_check_out=time(17, 0),
        )
        AttendanceCode.objects.create(tenant=self.tenant, code="H", label="Hadir")

    def test_ot_before_disabled_by_policy(self):
        self.assertFalse(ot_before_overtime_enabled(self.tenant, self.plant))

    def test_export_requires_date_range(self):
        self.client.login(username="tahap1admin", password="TestPassword123!")
        response = self.client.get(reverse("web:attendance_list"), {"export": "csv"})
        self.assertEqual(response.status_code, 302)
        follow = self.client.get(reverse("web:attendance_list"))
        self.assertContains(follow, "rentang tanggal")

    def test_export_with_date_range(self):
        work_date = date(2024, 6, 3)
        DailyTimesheet.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee=self.employee,
            work_date=work_date,
            shift_code="S1",
        )
        self.client.login(username="tahap1admin", password="TestPassword123!")
        response = self.client.get(
            reverse("web:attendance_list"),
            {
                "export": "csv",
                "date_from": "2024-06-01",
                "date_to": "2024-06-30",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        body = response.content.decode()
        self.assertIn("Budi Santoso", body)
        self.assertIn("Overtime Duration After Hourly Time Off Label", body)
        self.assertIn("Effective Working Hour", body)

    def test_attendance_correction_logs_audit(self):
        work_date = date(2024, 6, 10)
        ts = DailyTimesheet.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee=self.employee,
            work_date=work_date,
            shift_code="S1",
        )
        apply_attendance_correction(
            ts,
            check_in_time=time(8, 5),
            check_out_time=time(17, 10),
            shift=self.shift,
            actor=self.admin,
        )
        log = AuditLog.objects.filter(
            model_name="attendance.attendancerecord",
            action=AuditLog.Action.UPDATE,
        ).first()
        self.assertIsNotNone(log)
        self.assertIn("attendance_correction", log.changes)

    def test_correction_recalculates_timesheet(self):
        work_date = timezone.localdate()
        ts = DailyTimesheet.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee=self.employee,
            work_date=work_date,
        )
        apply_attendance_correction(
            ts,
            check_in_time=time(8, 0),
            check_out_time=time(17, 0),
            shift=self.shift,
        )
        record = AttendanceRecord.objects.get(employee=self.employee, work_date=work_date)
        self.assertIsNotNone(record.check_in)
        updated = DailyTimesheet.objects.get(pk=ts.pk)
        self.assertEqual(updated.shift_code, "S1")

    def test_attendance_list_shows_ot_columns(self):
        self.client.login(username="tahap1admin", password="TestPassword123!")
        response = self.client.get(reverse("web:attendance_list"))
        self.assertContains(response, "OT Before")
        self.assertContains(response, "OT After")
        self.assertContains(response, "Tampilkan foto")

    def test_attendance_correct_page_loads_for_admin(self):
        work_date = timezone.localdate()
        ts = DailyTimesheet.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee=self.employee,
            work_date=work_date,
            shift_code="S1",
        )
        self.client.login(username="tahap1admin", password="TestPassword123!")
        response = self.client.get(reverse("web:attendance_correct", args=[ts.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Koreksi Absensi")
        self.assertContains(response, "Budi Santoso")
        self.assertContains(response, "Jam masuk")

    def test_attendance_correct_post_updates_record(self):
        work_date = timezone.localdate()
        ts = DailyTimesheet.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee=self.employee,
            work_date=work_date,
            shift_code="S1",
        )
        self.client.login(username="tahap1admin", password="TestPassword123!")
        response = self.client.post(
            reverse("web:attendance_correct", args=[ts.pk]),
            {
                "check_in_time": "08:00",
                "check_out_time": "17:00",
                "shift": str(self.shift.pk),
            },
        )
        self.assertRedirects(response, reverse("web:attendance_list"))
        record = AttendanceRecord.objects.get(employee=self.employee, work_date=work_date)
        self.assertIsNotNone(record.check_in)
        self.assertIsNotNone(record.check_out)
