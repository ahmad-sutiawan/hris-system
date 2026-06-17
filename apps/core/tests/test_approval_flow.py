from datetime import date, time
from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.attendance.models import OvertimeType
from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.leave.models import LeaveRequest, LeaveType
from apps.organization.models import Department, JobPosition


class LeaveOvertimeApprovalFlowTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="approval", name="Approval Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="AP", name="Plant AP")
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
            username="mgr-approval",
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
            employee_id="AP-MGR",
            full_name="Manager Approval",
            user=self.manager_user,
            base_salary=Decimal("7000000"),
        )
        self.employee_user = User.objects.create_user(
            username="emp-approval",
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
            employee_id="AP-001",
            full_name="Employee Approval",
            user=self.employee_user,
            base_salary=Decimal("5000000"),
        )
        self.other_employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            job_position=self.job,
            employee_id="AP-002",
            full_name="Other Employee",
            base_salary=Decimal("4500000"),
        )
        self.leave_type = LeaveType.objects.create(
            tenant=self.tenant,
            code="CM",
            name="Cuti Menghamili",
            default_quota_days=Decimal("2"),
        )
        self.overtime_type = OvertimeType.objects.create(
            tenant=self.tenant,
            code="OT-HK-1",
            name="Lembur Hari Kerja",
            day_category=OvertimeType.DayCategory.WORKDAY,
            hour_from=1,
            hour_to=1,
            multiplier=Decimal("1.5"),
        )
        self.client = APIClient()

    def _login(self, user):
        self.client.force_authenticate(user=user)

    def test_employee_can_create_leave_without_employee_field(self):
        self._login(self.employee_user)
        response = self.client.post(
            "/api/v1/leave-requests/",
            {
                "leave_type": self.leave_type.pk,
                "start_date": "2026-06-18",
                "end_date": "2026-06-18",
                "is_half_day": True,
                "reason": "menghamili istri",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["employee"], self.employee.pk)
        self.assertEqual(data["status"], LeaveRequest.Status.PENDING)

    def test_manager_sees_and_approves_direct_report_leave(self):
        self._login(self.employee_user)
        create = self.client.post(
            "/api/v1/leave-requests/",
            {
                "leave_type": self.leave_type.pk,
                "start_date": "2026-06-20",
                "end_date": "2026-06-20",
                "reason": "cuti",
            },
            format="json",
        )
        leave_id = create.json()["id"]

        self._login(self.manager_user)
        listing = self.client.get("/api/v1/leave-requests/")
        self.assertEqual(listing.status_code, 200)
        ids = [row["id"] for row in listing.json()["results"]]
        self.assertIn(leave_id, ids)
        row = next(r for r in listing.json()["results"] if r["id"] == leave_id)
        self.assertTrue(row["can_approve"])

        approve = self.client.post(f"/api/v1/leave-requests/{leave_id}/approve/")
        self.assertEqual(approve.status_code, 200)
        self.assertEqual(approve.json()["status"], LeaveRequest.Status.APPROVED)

    def test_manager_cannot_approve_non_report_leave(self):
        self._login(self.employee_user)
        leave = LeaveRequest.objects.create(
            tenant=self.tenant,
            employee=self.other_employee,
            leave_type=self.leave_type,
            start_date=date(2026, 6, 21),
            end_date=date(2026, 6, 21),
            days=Decimal("1"),
            reason="test",
            status=LeaveRequest.Status.PENDING,
        )

        self._login(self.manager_user)
        listing = self.client.get("/api/v1/leave-requests/")
        ids = [row["id"] for row in listing.json()["results"]]
        self.assertNotIn(leave.id, ids)

        approve = self.client.post(f"/api/v1/leave-requests/{leave.id}/approve/")
        self.assertEqual(approve.status_code, 404)

    def test_manager_sees_and_approves_direct_report_overtime(self):
        self._login(self.employee_user)
        create = self.client.post(
            "/api/v1/overtime-requests/",
            {
                "overtime_type": self.overtime_type.pk,
                "work_date": "2026-06-19",
                "ot_before_minutes": 0,
                "ot_after_minutes": 60,
                "reason": "closing",
            },
            format="json",
        )
        self.assertEqual(create.status_code, 201, create.content)
        ot_id = create.json()["id"]

        self._login(self.manager_user)
        listing = self.client.get("/api/v1/overtime-requests/")
        row = next(r for r in listing.json()["results"] if r["id"] == ot_id)
        self.assertTrue(row["can_approve"])

        approve = self.client.post(f"/api/v1/overtime-requests/{ot_id}/approve/")
        self.assertEqual(approve.status_code, 200)
        self.assertEqual(approve.json()["status"], "approved")

    def test_leave_list_avoids_n_plus_one_on_can_approve(self):
        self._login(self.employee_user)
        for day in range(20, 25):
            self.client.post(
                "/api/v1/leave-requests/",
                {
                    "leave_type": self.leave_type.pk,
                    "start_date": f"2026-06-{day}",
                    "end_date": f"2026-06-{day}",
                    "reason": f"cuti {day}",
                },
                format="json",
            )

        self._login(self.manager_user)
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get("/api/v1/leave-requests/?page_size=20")
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertGreaterEqual(len(results), 5)
        self.assertTrue(all(r["can_approve"] for r in results))
        employee_queries = [
            q["sql"]
            for q in ctx.captured_queries
            if "employees_employee" in q["sql"].lower()
        ]
        self.assertLessEqual(len(employee_queries), 2)
