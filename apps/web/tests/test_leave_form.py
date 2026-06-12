from decimal import Decimal

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.leave.models import LeaveBalance, LeaveType
from apps.organization.models import Department, JobPosition


@override_settings(ALLOWED_HOSTS=["testserver"])
class LeaveFormBalanceTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.tenant = Tenant.objects.create(slug="leave-form", name="Leave Form Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.dept = Department.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="HR",
            name="HR",
        )
        self.job = JobPosition.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="OP",
            title="Operator",
            department=self.dept,
        )
        self.leave_type = LeaveType.objects.create(
            tenant=self.tenant,
            code="CT",
            name="Cuti Tahunan",
            default_quota_days=12,
        )
        self.employee_user = User.objects.create_user(
            username="budi-leave",
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
            full_name="Budi Leave",
            user=self.employee_user,
            base_salary=Decimal("5000000"),
            status=Employee.Status.PERMANENT,
        )
        self.year = timezone.localdate().year
        LeaveBalance.objects.create(
            tenant=self.tenant,
            employee=self.employee,
            leave_type=self.leave_type,
            year=self.year,
            opening_balance=Decimal("12"),
            accrued=Decimal("0"),
            used=Decimal("2"),
            pending=Decimal("1"),
            remaining=Decimal("9"),
        )
        self.admin = User.objects.create_user(
            username="admin-leave",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.ADMIN,
        )

    def test_employee_sees_own_leave_balances(self):
        self.client.login(username="budi-leave", password="TestPassword123!")
        response = self.client.get(reverse("web:leave_create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Saldo Cuti Tahun Berjalan")
        self.assertContains(response, "Budi Leave (P1-001)")
        self.assertContains(response, "CT")
        self.assertContains(response, "9")

    def test_hr_sees_each_employee_leave_balances(self):
        self.client.login(username="admin-leave", password="TestPassword123!")
        response = self.client.get(reverse("web:leave_create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "leave-balances-by-employee")
        self.assertContains(response, "Budi Leave (P1-001)")
        self.assertContains(response, '"remaining": "9"')
