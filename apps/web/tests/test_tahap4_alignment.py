"""Tahap 4 — HR vs Payroll UI split."""

from datetime import date

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.organization.models import Department, JobPosition


@override_settings(ALLOWED_HOSTS=["testserver"])
class Tahap4PayrollSplitTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.tenant = Tenant.objects.create(slug="t4", name="T4 Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.dept = Department.objects.create(
            tenant=self.tenant, plant=self.plant, code="HR", name="HR"
        )
        self.job = JobPosition.objects.create(
            tenant=self.tenant, plant=self.plant, code="OP", title="Operator", department=self.dept
        )
        self.manager = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            job_position=self.job,
            employee_id="MGR",
            full_name="Manager",
            nik="N/A",
            email="m@test.com",
            phone="081",
            gender=Employee.Gender.NA,
            marital_status=Employee.MaritalStatus.NA,
            birth_place="N/A",
            join_date=date(2024, 1, 1),
        )
        self.admin = User.objects.create_user(
            username="t4admin",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.ADMIN,
        )

    def _employee_form(self, **overrides):
        data = {
            "employee_id": "E-T4",
            "full_name": "T4 Worker",
            "nik": "3201010101010001",
            "email": "t4@test.com",
            "phone": "08123456789",
            "address": "Jakarta",
            "mother_name": "Ibu T4",
            "birth_place": "Jakarta",
            "birth_date": "1990-01-01",
            "gender": Employee.Gender.MALE,
            "marital_status": Employee.MaritalStatus.SINGLE,
            "plant": self.plant.pk,
            "department": self.dept.pk,
            "job_position": self.job.pk,
            "manager": self.manager.pk,
            "join_date": "2024-06-01",
            "status": Employee.Status.PERMANENT,
        }
        data.update(overrides)
        return data

    def test_employee_list_hr_columns_no_salary(self):
        Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            job_position=self.job,
            employee_id="E1",
            full_name="Worker",
            base_salary="5000000",
        )
        self.client.login(username="t4admin", password="TestPassword123!")
        response = self.client.get(reverse("web:employee_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Job Level")
        self.assertContains(response, "Data Gaji Karyawan")
        self.assertNotContains(response, "Gaji Pokok")
        self.assertNotContains(response, "Akun login")

    def test_create_redirects_to_compensation(self):
        self.client.login(username="t4admin", password="TestPassword123!")
        response = self.client.post(reverse("web:employee_create"), self._employee_form())
        self.assertEqual(response.status_code, 302)
        self.assertIn("/payroll/compensation/", response.url)
        emp = Employee.objects.get(employee_id="E-T4")
        comp_response = self.client.get(reverse("web:employee_compensation_edit", args=[emp.pk]))
        self.assertEqual(comp_response.status_code, 200)
        self.assertContains(comp_response, "Gaji & Tunjangan")

    def test_compensation_list_export(self):
        Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="E2",
            full_name="Pay Worker",
            tax_status="TK/0",
        )
        self.client.login(username="t4admin", password="TestPassword123!")
        response = self.client.get(reverse("web:employee_compensation_list"), {"export": "csv"})
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Pay Worker", body)
        self.assertIn("PTKP", body)

    def test_employee_export_hr_fields(self):
        Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            employee_id="E3",
            full_name="Export Worker",
            mother_name="Ibu Export",
        )
        self.client.login(username="t4admin", password="TestPassword123!")
        response = self.client.get(reverse("web:employee_list"), {"export": "csv"})
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Employee ID", body)
        self.assertIn("Organization", body)
        self.assertIn("Status Employee", body)
        self.assertIn("Branch Name", body)
        self.assertNotIn("Base Salary", body)
