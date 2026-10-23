from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import Tenant, User
from apps.employees.models import Employee


class AuthMeNullProfileTests(TestCase):
    def test_me_allows_employee_without_org_or_shift(self):
        tenant = Tenant.objects.create(slug="me-null", name="Me Null")
        user = User.objects.create_user(
            username="me-null-user",
            password="not-used",
            tenant=tenant,
            role=User.Role.EMPLOYEE,
        )
        Employee.objects.create(
            tenant=tenant,
            user=user,
            employee_id="ME-NULL",
            full_name="Tanpa Relasi",
        )
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/v1/auth/me/")

        self.assertEqual(response.status_code, 200, response.content[:500])
        employee = response.data["employee"]
        self.assertIsNone(employee["photo_url"])
        self.assertIsNone(employee["plant"])
        self.assertIsNone(employee["department"])
        self.assertIsNone(employee["job_position"])
        self.assertIsNone(employee["manager"])
