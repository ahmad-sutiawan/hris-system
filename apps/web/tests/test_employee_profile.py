from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.leave.models import LeaveType
from apps.organization.models import Department


class EmployeeProfileViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Profile Co", slug="profileco")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.dept = Department.objects.create(
            tenant=self.tenant, plant=self.plant, code="D1", name="Prod"
        )
        self.user = User.objects.create_user(
            username="emp-profile",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.EMPLOYEE,
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            employee_id="E-PROF",
            full_name="Profile Worker",
            base_salary=Decimal("4500000"),
            user=self.user,
        )
        LeaveType.objects.create(
            tenant=self.tenant, code="CT", name="Cuti Tahunan", default_quota_days=12
        )

    def test_employee_can_open_profile(self):
        self.client.login(username="emp-profile", password="TestPassword123!")
        response = self.client.get(reverse("web:employee_profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Profile Worker")
        self.assertContains(response, "E-PROF")
        self.assertContains(response, "Komponen Gaji")

    def test_admin_without_profile_sees_message(self):
        admin = User.objects.create_user(
            username="admin-no-prof",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.ADMIN,
        )
        self.client.login(username="admin-no-prof", password="TestPassword123!")
        response = self.client.get(reverse("web:employee_profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "belum terhubung")

    def test_profile_page_in_sidebar(self):
        self.client.login(username="emp-profile", password="TestPassword123!")
        response = self.client.get(reverse("web:dashboard"))
        self.assertContains(response, reverse("web:employee_profile"))
        self.assertContains(response, "Profil Karyawan")
