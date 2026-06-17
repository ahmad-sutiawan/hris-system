"""Tahap 3 — mandatory defaults and employee master completeness."""

from datetime import date

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.employees.services.mandatory_defaults import NA, apply_mandatory_defaults, backfill_all_employees
from apps.organization.models import Department, JobPosition


@override_settings(ALLOWED_HOSTS=["testserver"])
class Tahap3MandatoryDefaultsTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="t3", name="T3 Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.dept = Department.objects.create(
            tenant=self.tenant, plant=self.plant, code="HR", name="HR"
        )
        self.job = JobPosition.objects.create(
            tenant=self.tenant, plant=self.plant, code="OP", title="Operator", department=self.dept
        )
        self.admin = User.objects.create_user(
            username="t3admin",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.ADMIN,
        )

    def test_backfill_fills_na_for_blank_fields(self):
        employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="E-NA",
            full_name="Incomplete Worker",
        )
        apply_mandatory_defaults(employee, fill_fk=True)
        employee.save()
        employee.refresh_from_db()
        self.assertEqual(employee.nik, NA)
        self.assertEqual(employee.email, NA)
        self.assertEqual(employee.gender, Employee.Gender.NA)
        self.assertEqual(employee.department_id, self.dept.pk)
        self.assertEqual(employee.job_position_id, self.job.pk)

    def test_backfill_command(self):
        Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="E-CMD",
            full_name="Cmd Worker",
        )
        stats = backfill_all_employees(tenant=self.tenant)
        self.assertGreaterEqual(stats["updated"], 1)

    def test_employee_edit_shows_document_upload(self):
        employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            job_position=self.job,
            employee_id="E-DOC",
            full_name="Doc Worker",
            nik=NA,
            email=NA,
            phone=NA,
            gender=Employee.Gender.NA,
            marital_status=Employee.MaritalStatus.NA,
            birth_place=NA,
            join_date=date(2024, 1, 1),
        )
        self.client.login(username="t3admin", password="TestPassword123!")
        response = self.client.get(reverse("web:employee_edit", args=[employee.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload KTP")
        self.assertContains(response, "Data Gaji Karyawan")

    def test_compensation_list_renders(self):
        Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="E-PAY",
            full_name="Pay Worker",
        )
        self.client.login(username="t3admin", password="TestPassword123!")
        response = self.client.get(reverse("web:employee_compensation_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Data Gaji Karyawan")
