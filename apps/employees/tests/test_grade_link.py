from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.core.models import Plant, Tenant
from apps.employees.models import Employee
from apps.organization.models import Department, EmployeeGrade


class EmployeeGradeLinkTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Link Co", slug="linkco")
        self.plant_a = Plant.objects.create(tenant=self.tenant, code="PA", name="Plant A")
        self.plant_b = Plant.objects.create(tenant=self.tenant, code="PB", name="Plant B")
        self.dept = Department.objects.create(
            tenant=self.tenant, plant=self.plant_a, code="D1", name="Prod"
        )
        self.grade_a = EmployeeGrade.objects.create(
            tenant=self.tenant,
            plant=self.plant_a,
            code="G2",
            name="Operator",
            daily_wage=Decimal("200000"),
        )
        self.grade_b = EmployeeGrade.objects.create(
            tenant=self.tenant,
            plant=self.plant_b,
            code="G2",
            name="Operator B",
            daily_wage=Decimal("210000"),
        )

    def test_employee_stores_grade_fk(self):
        employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant_a,
            department=self.dept,
            employee_grade=self.grade_a,
            employee_id="E1",
            full_name="Worker",
            salary_scheme=Employee.SalaryScheme.DAILY,
            base_salary=Decimal("180000"),
        )
        employee.refresh_from_db()
        self.assertEqual(employee.employee_grade_id, self.grade_a.pk)
        self.assertEqual(employee.grade_label, "G2 — Operator")

    def test_grade_must_match_employee_plant(self):
        employee = Employee(
            tenant=self.tenant,
            plant=self.plant_a,
            department=self.dept,
            employee_grade=self.grade_b,
            employee_id="E2",
            full_name="Mismatch",
        )
        with self.assertRaises(ValidationError):
            employee.full_clean()
