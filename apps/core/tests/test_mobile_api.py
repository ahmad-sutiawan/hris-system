from datetime import date, time
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import Announcement, Plant, Tenant, User
from apps.employees.models import Employee
from apps.organization.models import Department, JobPosition
from apps.shifts.models import Shift, ShiftAssignment


class MobileDashboardApiTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="mobile", name="Mobile Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="SM", name="Office-SM")
        self.dept = Department.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="OPS",
            name="Operations",
        )
        self.job = JobPosition.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="STF",
            title="Staff",
            department=self.dept,
        )
        self.manager_user = User.objects.create_user(
            username="mgr-mobile",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.MANAGER,
        )
        self.manager = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            job_position=self.job,
            employee_id="SM-MGR",
            full_name="Manager Mobile",
            user=self.manager_user,
            base_salary=Decimal("7000000"),
        )
        self.employee_user = User.objects.create_user(
            username="emp-mobile",
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
            manager=self.manager,
            employee_id="SM-001",
            full_name="Employee Mobile",
            user=self.employee_user,
            base_salary=Decimal("5000000"),
        )
        self.report = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            job_position=self.job,
            manager=self.manager,
            employee_id="SM-002",
            full_name="Report Mobile",
            base_salary=Decimal("4500000"),
        )
        self.shift = Shift.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="D1",
            name="Shift Pagi",
            scheduled_check_in=time(8, 0),
            scheduled_check_out=time(16, 0),
        )
        today = timezone.localdate()
        ShiftAssignment.objects.create(
            tenant=self.tenant,
            employee=self.employee,
            shift=self.shift,
            work_date=today,
            scheduled_check_in=time(8, 0),
            scheduled_check_out=time(16, 0),
        )
        Announcement.objects.create(
            tenant=self.tenant,
            title="Info HR",
            summary="Update kebijakan cuti",
            body="Detail kebijakan",
            is_active=True,
            publish_start=timezone.now(),
        )
        self.client = APIClient()

    def _login(self, user):
        self.client.force_authenticate(user=user)

    def test_dashboard_includes_shift_team_and_announcements(self):
        self._login(self.employee_user)
        response = self.client.get("/api/v1/mobile/dashboard/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["today_shift"]["plant_name"], "Office-SM")
        self.assertTrue(data["today_shift"]["scheduled_check_in"].startswith(timezone.localdate().isoformat()))
        self.assertGreaterEqual(len(data["featured_announcements"]), 1)
        self.assertGreaterEqual(len(data["upcoming_shifts"]), 1)
        self.assertIn("pending_requests", data)

        self._login(self.manager_user)
        manager_data = self.client.get("/api/v1/mobile/dashboard/").json()
        self.assertGreaterEqual(len(manager_data["direct_reports"]), 1)

    def test_employee_sees_colleagues_when_no_reports(self):
        self._login(self.employee_user)
        response = self.client.get("/api/v1/mobile/dashboard/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["direct_reports"], [])
        self.assertGreaterEqual(len(data["team_colleagues"]), 1)

    def test_dashboard_avoids_redundant_shift_query(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        self._login(self.employee_user)
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get("/api/v1/mobile/dashboard/")
        self.assertEqual(response.status_code, 200)
        shift_queries = [
            q["sql"]
            for q in ctx.captured_queries
            if "shifts_shiftassignment" in q["sql"].lower()
        ]
        self.assertLessEqual(len(shift_queries), 2)
