from decimal import Decimal

from django.contrib.auth import authenticate
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.core.auth_login import apply_employee_credentials, find_employee_by_login_identifier
from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.leave.models import LeaveType
from apps.organization.models import Department, JobPosition


@override_settings(ALLOWED_HOSTS=["testserver"])
class EmployeeLoginTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.tenant = Tenant.objects.create(slug="login-test", name="Login Test Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.dept = Department.objects.create(
            tenant=self.tenant, plant=self.plant, code="HR", name="HR"
        )
        self.job = JobPosition.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            code="STF",
            title="Staff",
        )
        self.admin = User.objects.create_user(
            username="admin",
            password="Admin123456!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.ADMIN,
        )
        self.employee, _ = Employee.objects.update_or_create(
            tenant=self.tenant,
            employee_id="PLT01-2026-001",
            defaults={
                "plant": self.plant,
                "department": self.dept,
                "job_position": self.job,
                "full_name": "Budi Santoso",
                "nik": "3201010101900001",
                "join_date": "2026-01-01",
                "status": Employee.Status.PERMANENT,
            },
        )
        apply_employee_credentials(self.employee, role=User.Role.EMPLOYEE)
        LeaveType.objects.create(
            tenant=self.tenant,
            code="CT",
            name="Cuti Tahunan",
            default_quota_days=Decimal("12"),
        )

    def test_login_with_employee_id(self):
        user = authenticate(username="PLT01-2026-001", password="PLT01-2026-001")
        self.assertIsNotNone(user)
        self.assertEqual(user.pk, self.employee.user_id)

    def test_login_with_nik(self):
        user = authenticate(username="3201010101900001", password="PLT01-2026-001")
        self.assertIsNotNone(user)
        self.assertEqual(user.pk, self.employee.user_id)

    def test_admin_still_uses_username(self):
        user = authenticate(username="admin", password="Admin123456!")
        self.assertIsNotNone(user)
        self.assertEqual(user.pk, self.admin.pk)

    def test_admin_not_found_by_nik_lookup(self):
        self.assertIsNone(find_employee_by_login_identifier("admin"))

    def test_web_login_employee_by_nik(self):
        response = self.client.post(
            reverse("web:login"),
            {"username": "3201010101900001", "password": "PLT01-2026-001"},
        )
        self.assertRedirects(response, reverse("web:dashboard"))

    def test_web_login_admin(self):
        response = self.client.post(
            reverse("web:login"),
            {"username": "admin", "password": "Admin123456!"},
        )
        self.assertRedirects(response, reverse("web:dashboard"))

    def test_login_with_short_employee_id(self):
        short, _ = Employee.objects.update_or_create(
            tenant=self.tenant,
            employee_id="525",
            defaults={
                "plant": self.plant,
                "department": self.dept,
                "job_position": self.job,
                "full_name": "Ahmad Sutiawan Test",
                "nik": "3604161001000002",
                "join_date": "2026-01-01",
                "status": Employee.Status.PERMANENT,
            },
        )
        apply_employee_credentials(short, role=User.Role.EMPLOYEE)
        user = authenticate(username="3604161001000002", password="525")
        self.assertIsNotNone(user)
        self.assertEqual(user.pk, short.user_id)

    def test_jwt_token_employee_by_employee_id(self):
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": "PLT01-2026-001", "password": "PLT01-2026-001"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())

    def test_legacy_username_cannot_login(self):
        legacy = User.objects.create_user(
            username="budi",
            password="Employee123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.EMPLOYEE,
        )
        self.employee.user = legacy
        self.employee.save(update_fields=["user", "updated_at"])
        user = authenticate(username="budi", password="Employee123!")
        self.assertIsNone(user)

    def test_login_with_nik_and_employee_id_like_production(self):
        """Contoh data nyata: NIK 16 digit + Employee ID numerik."""
        prod, _ = Employee.objects.update_or_create(
            tenant=self.tenant,
            employee_id="1704",
            defaults={
                "plant": self.plant,
                "department": self.dept,
                "job_position": self.job,
                "full_name": "Aan Ansori",
                "nik": "3604231902010003",
                "join_date": "2026-01-01",
                "status": Employee.Status.PERMANENT,
            },
        )
        apply_employee_credentials(prod, role=User.Role.EMPLOYEE)
        user = authenticate(username="3604231902010003", password="1704")
        self.assertIsNotNone(user)
        self.assertEqual(user.pk, prod.user_id)

    def test_dashboard_then_punch_keeps_session(self):
        """Regression: dashboard must not reset password and log user out on punch."""
        from apps.attendance.tests.test_punch_photo import _sample_photo_data_url
        from apps.employees.services.onboarding import employee_leave_balances_summary

        user = self.employee.user
        hash_before = user.get_session_auth_hash()

        self.client.post(
            reverse("web:login"),
            {"username": "3201010101900001", "password": "PLT01-2026-001"},
        )
        response = self.client.get(reverse("web:dashboard"))
        self.assertEqual(response.status_code, 200)

        employee_leave_balances_summary(self.employee)
        user.refresh_from_db()
        self.assertEqual(user.get_session_auth_hash(), hash_before)

        response = self.client.post(
            reverse("web:punch"),
            {"action": "in", "photo": _sample_photo_data_url()},
        )
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("/login/", response.url)
        follow = self.client.get(reverse("web:dashboard"))
        self.assertEqual(follow.status_code, 200)
