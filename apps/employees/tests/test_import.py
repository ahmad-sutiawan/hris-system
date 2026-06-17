from decimal import Decimal
from io import StringIO

from django.test import TestCase

from apps.core.models import Plant, Tenant
from apps.employees.models import Employee
from apps.employees.services.import_csv import import_employees_csv, template_csv
from apps.organization.models import Department, JobPosition
from apps.payroll.models import PayrollRun, Payslip
from apps.payroll.services.payslip_pdf import generate_payslip_pdf


class ImportCsvTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="T", slug="t2")
        self.plant = Plant.objects.create(tenant=self.tenant, code="PLT01", name="Plant")
        Department.objects.create(
            tenant=self.tenant, plant=self.plant, code="PROD", name="Production"
        )
        JobPosition.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="OPR",
            title="Operator",
        )

    def test_template_has_headers(self):
        content = template_csv()
        self.assertIn("employee_id", content)

    def test_import_creates_employee(self):
        content = template_csv()
        result = import_employees_csv(self.tenant, content)
        self.assertEqual(result["created"], 1)
        employee = Employee.objects.get(tenant=self.tenant)
        self.assertEqual(employee.salary_scheme, Employee.SalaryScheme.DAILY)
        self.assertEqual(employee.base_salary, Decimal("200000"))
        self.assertEqual(employee.allowance_meal, Decimal("25000"))
        self.assertEqual(employee.bpjs_kesehatan_number, "0001234567890")


class PayslipPdfTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="T", slug="t3")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant")
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="E1",
            full_name="Test",
            base_salary=Decimal("5000000"),
        )
        self.run = PayrollRun.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            period_start="2026-06-01",
            period_end="2026-06-30",
        )
        self.payslip = Payslip.objects.create(
            tenant=self.tenant,
            payroll_run=self.run,
            employee=self.employee,
            gross_amount=Decimal("5000000"),
            deduction_amount=Decimal("200000"),
            net_amount=Decimal("4800000"),
            earnings_breakdown={"base_salary": "5000000"},
            deductions_breakdown={"bpjs_kesehatan": "200000"},
            verification_hash="abc123",
        )

    def test_generate_pdf_bytes(self):
        pdf = generate_payslip_pdf(self.payslip)
        self.assertTrue(pdf.startswith(b"%PDF"))
