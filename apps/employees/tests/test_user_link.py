from django.test import TestCase, override_settings

from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.employees.services.user_link import (
    ensure_employee_profile,
    link_user_to_employee,
)


class UserLinkTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="link", name="Link Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.user = User.objects.create_user(
            username="ayub",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.EMPLOYEE,
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="P1-AYUB",
            full_name="Ayub Employee",
            email="ayub@demo.local",
        )

    def test_link_by_username_in_full_name(self):
        linked = link_user_to_employee(self.user)
        self.assertIsNotNone(linked)
        self.assertEqual(linked.pk, self.employee.pk)
        self.user.refresh_from_db()
        self.assertEqual(self.user.employee_profile.pk, self.employee.pk)

    def test_link_by_email(self):
        self.employee.full_name = "Someone Else"
        self.employee.save(update_fields=["full_name"])
        self.user.email = "ayub@demo.local"
        self.user.save(update_fields=["email"])
        linked = link_user_to_employee(self.user)
        self.assertEqual(linked.pk, self.employee.pk)

    def test_link_by_employee_id(self):
        self.employee.full_name = "Someone Else"
        self.employee.email = ""
        self.employee.employee_id = "ayub"
        self.employee.save()
        self.user.username = "ayub"
        self.user.save()
        linked = link_user_to_employee(self.user)
        self.assertEqual(linked.pk, self.employee.pk)

    @override_settings(HRIS_AUTO_PROVISION_EMPLOYEES=True)
    def test_provision_creates_employee_when_no_match(self):
        self.employee.delete()
        self.user.refresh_from_db()
        profile = ensure_employee_profile(self.user)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.user_id, self.user.pk)
        self.assertTrue(profile.employee_id.startswith("P1-AYUB"))

    @override_settings(HRIS_AUTO_PROVISION_EMPLOYEES=False)
    def test_ensure_does_not_provision_when_disabled(self):
        self.employee.delete()
        self.user.refresh_from_db()
        profile = ensure_employee_profile(self.user)
        self.assertIsNone(profile)
        self.assertFalse(Employee.objects.filter(user=self.user).exists())
