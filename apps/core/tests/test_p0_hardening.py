"""P0 production hardening — API authorization and timesheet lock."""

from datetime import date, time
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.attendance.models import DailyTimesheet
from apps.attendance.services.timesheet import recalculate_daily_timesheet
from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.payroll.models import PayrollRun


class ApiAuthorizationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tenant = Tenant.objects.create(slug="p0", name="P0 Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant")
        self.hr = User.objects.create_user(
            username="p0hr",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.HR,
        )
        self.worker_user = User.objects.create_user(
            username="p0worker",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.EMPLOYEE,
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="E1",
            full_name="Worker",
            user=self.worker_user,
            join_date=date(2024, 1, 1),
            base_salary=Decimal("5000000"),
        )
        self.run = PayrollRun.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
        )

    def test_employee_cannot_patch_own_salary(self):
        self.client.force_authenticate(self.worker_user)
        response = self.client.patch(
            f"/api/v1/employees/{self.employee.pk}/",
            {"base_salary": "99999999"},
            format="json",
        )
        self.assertIn(response.status_code, {403, 405})
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.base_salary, Decimal("5000000"))

    def test_employee_cannot_finalize_payroll(self):
        self.client.force_authenticate(self.worker_user)
        response = self.client.post(f"/api/v1/payroll-runs/{self.run.pk}/finalize/")
        self.assertEqual(response.status_code, 403)
        self.run.refresh_from_db()
        self.assertNotEqual(self.run.status, PayrollRun.Status.FINALIZED)

    def test_hr_can_list_payroll_runs(self):
        self.client.force_authenticate(self.hr)
        response = self.client.get("/api/v1/payroll-runs/")
        self.assertEqual(response.status_code, 200)

    def test_employee_cannot_create_shift(self):
        self.client.force_authenticate(self.worker_user)
        response = self.client.post(
            "/api/v1/shifts/",
            {"code": "MAL", "name": "Malicious Shift", "plant": self.plant.pk},
            format="json",
        )
        self.assertIn(response.status_code, {403, 405})

    def test_employee_cannot_create_attendance_directly(self):
        self.client.force_authenticate(self.worker_user)
        response = self.client.post(
            "/api/v1/attendance/",
            {
                "employee": self.employee.pk,
                "work_date": "2026-06-18",
                "check_in": "2026-06-18T07:00:00+07:00",
            },
            format="json",
        )
        self.assertIn(response.status_code, {403, 405})


class TimesheetLockTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="lock", name="Lock Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant")
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="E1",
            full_name="Worker",
            join_date=date(2024, 1, 1),
        )
        self.work_date = date(2026, 6, 10)
        self.timesheet = DailyTimesheet.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee=self.employee,
            work_date=self.work_date,
            shift_code="PAGI",
            check_in=timezone.make_aware(timezone.datetime.combine(self.work_date, time(7, 0))),
            paid_working_hours=Decimal("8"),
            calculation_status=DailyTimesheet.CalculationStatus.LOCKED,
            locked_at=timezone.now(),
        )

    def test_locked_timesheet_not_recalculated(self):
        result = recalculate_daily_timesheet(self.employee, self.work_date)
        self.assertEqual(result.pk, self.timesheet.pk)
        self.assertEqual(result.calculation_status, DailyTimesheet.CalculationStatus.LOCKED)
        self.assertEqual(result.paid_working_hours, Decimal("8"))
