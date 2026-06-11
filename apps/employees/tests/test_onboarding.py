from datetime import time
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.core.models import Plant, Tenant
from apps.employees.models import Employee
from apps.employees.services.onboarding import (
    assign_default_shift,
    employee_leave_balances_summary,
    provision_new_employee,
)
from apps.shifts.models import Shift, ShiftAssignment
from apps.leave.models import LeaveBalance, LeaveType
from apps.organization.models import Department, JobPosition


class OnboardingServiceTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="onboard", name="Onboard Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant")
        self.dept = Department.objects.create(
            tenant=self.tenant, plant=self.plant, code="HR", name="HR"
        )
        self.job = JobPosition.objects.create(
            tenant=self.tenant, plant=self.plant, code="OP", title="Operator", department=self.dept
        )
        self.leave_ct = LeaveType.objects.create(
            tenant=self.tenant,
            code="CT",
            name="Cuti Tahunan",
            default_quota_days=Decimal("12"),
        )
        self.leave_cs = LeaveType.objects.create(
            tenant=self.tenant,
            code="CS",
            name="Cuti Sakit",
            default_quota_days=Decimal("0"),
        )
        self.shift = Shift.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            name="Pagi",
            code="PAGI",
            scheduled_check_in=time(7, 0),
            scheduled_check_out=time(15, 0),
        )
        self.plant.default_shift = self.shift
        self.plant.save(update_fields=["default_shift"])
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            job_position=self.job,
            employee_id="P1-001",
            full_name="New Hire",
        )

    def test_provision_creates_all_active_leave_balances(self):
        balances = provision_new_employee(self.employee)
        self.assertEqual(len(balances), 2)
        ct = LeaveBalance.objects.get(employee=self.employee, leave_type=self.leave_ct)
        self.assertEqual(ct.remaining, Decimal("12"))
        cs = LeaveBalance.objects.get(employee=self.employee, leave_type=self.leave_cs)
        self.assertEqual(cs.remaining, Decimal("0"))

    def test_summary_ensures_balances_exist(self):
        summary = employee_leave_balances_summary(self.employee)
        self.assertEqual(len(summary), 2)
        codes = {row.leave_type.code for row in summary}
        self.assertEqual(codes, {"CT", "CS"})

    def test_provision_with_shift_assigns_join_date(self):
        self.employee.join_date = timezone.localdate()
        self.employee.save(update_fields=["join_date"])
        provision_new_employee(self.employee, assign_shift=True)
        self.assertTrue(
            ShiftAssignment.objects.filter(
                employee=self.employee, work_date=self.employee.join_date
            ).exists()
        )

    def test_assign_default_shift_uses_plant_default(self):
        assignment = assign_default_shift(self.employee)
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.shift_id, self.shift.pk)

    def test_skips_inactive_employee(self):
        self.employee.status = Employee.Status.INACTIVE
        self.employee.save(update_fields=["status"])
        balances = provision_new_employee(self.employee)
        self.assertEqual(balances, [])
        self.assertFalse(LeaveBalance.objects.filter(employee=self.employee).exists())
