from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.attendance.models import AttendanceRecord
from apps.attendance.services.timesheet import recalculate_daily_timesheet
from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.organization.models import Department, JobPosition


@override_settings(MEDIA_ROOT="/tmp/hris-test-media")
class TimesheetApiTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="ts", name="TS Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.dept = Department.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="OPS",
            name="Ops",
        )
        self.job = JobPosition.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="STF",
            title="Staff",
            department=self.dept,
        )
        self.user = User.objects.create_user(
            username="ts-user",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.EMPLOYEE,
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            job_position=self.job,
            employee_id="P1-001",
            full_name="Timesheet User",
            user=self.user,
            base_salary=Decimal("5000000"),
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _create_day(self, work_date, *, with_photos=False):
        record = AttendanceRecord.objects.create(
            tenant=self.tenant,
            employee=self.employee,
            plant=self.plant,
            work_date=work_date,
            check_in=timezone.make_aware(
                timezone.datetime.combine(
                    work_date,
                    timezone.datetime.min.time().replace(hour=8),
                )
            ),
            check_out=timezone.make_aware(
                timezone.datetime.combine(
                    work_date,
                    timezone.datetime.min.time().replace(hour=17),
                )
            ),
            source=AttendanceRecord.Source.MOBILE,
        )
        if with_photos:
            record.check_in_photo.save("in.jpg", ContentFile(b"fake-in"), save=True)
            record.check_out_photo.save("out.jpg", ContentFile(b"fake-out"), save=True)
        return recalculate_daily_timesheet(self.employee, work_date)

    def test_timesheet_list_includes_photo_urls_and_date_filter(self):
        today = timezone.localdate()
        old = today - timedelta(days=40)
        self._create_day(today, with_photos=True)
        self._create_day(old, with_photos=False)

        response = self.client.get(
            "/api/v1/timesheets/",
            {
                "work_date_from": (today - timedelta(days=7)).isoformat(),
                "work_date_to": today.isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)
        rows = response.json()["results"]
        self.assertEqual(len(rows), 1)
        self.assertIn("check_in_photo_url", rows[0])
        self.assertTrue(rows[0]["check_in_photo_url"])
        self.assertEqual(rows[0]["punch_source"], "mobile")

        old_response = self.client.get(
            "/api/v1/timesheets/",
            {
                "work_date_from": (old - timedelta(days=1)).isoformat(),
                "work_date_to": (old + timedelta(days=1)).isoformat(),
            },
        )
        self.assertEqual(len(old_response.json()["results"]), 1)
        self.assertIsNone(old_response.json()["results"][0]["check_in_photo_url"])
