from datetime import date, time
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import Announcement, Plant, Tenant, User
from apps.employees.models import Employee
from apps.leave.models import LeaveRequest, LeaveType
from apps.organization.models import Department, JobPosition
from apps.payroll.services.ter import seed_ter_master
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
        self.assertIn("pending_approvals", data)

        self._login(self.manager_user)
        manager_data = self.client.get("/api/v1/mobile/dashboard/").json()
        self.assertGreaterEqual(len(manager_data["direct_reports"]), 1)
        self.assertIn("pending_approvals", manager_data)

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

    def test_manager_pending_approvals_when_report_submits_leave(self):
        leave_type = LeaveType.objects.create(
            tenant=self.tenant,
            code="CT",
            name="Cuti Tahunan",
            default_quota_days=12,
        )
        LeaveRequest.objects.create(
            tenant=self.tenant,
            employee=self.report,
            leave_type=leave_type,
            start_date=timezone.localdate(),
            end_date=timezone.localdate(),
            days=Decimal("1"),
            reason="Cuti",
            status=LeaveRequest.Status.PENDING,
        )
        self._login(self.manager_user)
        data = self.client.get("/api/v1/mobile/dashboard/").json()
        self.assertGreaterEqual(data["pending_approvals"]["leave"], 1)


class MobileProfileApiTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="mobile-prof", name="Mobile Prof Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="SP", name="Plant SP")
        self.dept = Department.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="PRODUKSI",
            name="Produksi",
        )
        self.job = JobPosition.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="OPR",
            title="Operator",
            department=self.dept,
        )
        self.shift = Shift.objects.create(
            tenant=self.tenant,
            code="SORE",
            name="Shift Sore",
            scheduled_check_in=time(15, 0),
            scheduled_check_out=time(23, 0),
        )
        self.plant.default_shift = self.shift
        self.plant.save(update_fields=["default_shift"])
        self.user = User.objects.create_user(
            username="emp-prof",
            password="TestPassword123!",
            tenant=self.tenant,
            role=User.Role.EMPLOYEE,
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            job_position=self.job,
            employee_id="SP-001",
            full_name="Profil Mobile",
            user=self.user,
            base_salary=Decimal("5000000"),
            default_shift=self.shift,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_profile_returns_salary_preview_and_tax_fields(self):
        seed_ter_master(self.tenant)
        self.employee.tax_status = "TK/0"
        self.employee.base_salary = Decimal("7000000")
        self.employee.save(update_fields=["tax_status", "base_salary"])
        response = self.client.get("/api/v1/mobile/profile/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        employee = data["employee"]
        self.assertEqual(employee["tax_status"], "TK/0")
        self.assertIn("base_salary", employee)
        self.assertIn("salary_preview", data)
        preview = data["salary_preview"]
        self.assertIn("gross", preview)
        self.assertIn("net", preview)
        self.assertIn("deductions", preview)
        self.assertIn("pph21", preview)
        self.assertNotIn("grade", employee)

    def test_profile_returns_department_name_and_default_shift(self):
        response = self.client.get("/api/v1/mobile/profile/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        employee = data["employee"]
        self.assertEqual(employee["department"], "Produksi")
        self.assertEqual(employee["department_name"], "Produksi")
        self.assertEqual(employee["default_shift"]["code"], "SORE")
        self.assertEqual(employee["default_shift"]["source"], "employee")
        self.assertIsNotNone(data["today_assignment"])
        self.assertEqual(data["today_assignment"]["shift_code"], "SORE")

    def test_dashboard_falls_back_to_default_shift_when_no_assignment(self):
        response = self.client.get("/api/v1/mobile/dashboard/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["today_shift"]["shift_code"], "SORE")
        self.assertTrue(data["today_shift"].get("is_preview"))
