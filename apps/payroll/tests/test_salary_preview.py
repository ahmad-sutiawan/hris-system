from decimal import Decimal

from django.test import TestCase

from apps.core.models import Plant, Tenant
from apps.employees.models import Employee
from apps.organization.models import Department
from apps.payroll.services.salary_preview import build_salary_preview
from apps.payroll.services.ter import seed_ter_master


class SalaryPreviewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Preview Co", slug="previewco")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant")
        self.dept = Department.objects.create(
            tenant=self.tenant, plant=self.plant, code="D1", name="Prod"
        )
        seed_ter_master(self.tenant)

    def test_monthly_preview_includes_bpjs_and_pph21(self):
        employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            employee_id="E-M",
            full_name="Monthly Staff",
            salary_scheme=Employee.SalaryScheme.MONTHLY,
            base_salary=Decimal("7000000"),
            allowance_transport=Decimal("500000"),
            tax_status="TK/0",
        )
        preview = build_salary_preview(employee, tenant=self.tenant)
        self.assertEqual(preview["gross"], Decimal("7500000.00"))
        self.assertTrue(any(d["key"] == "bpjs_kesehatan" for d in preview["deductions"]))
        self.assertTrue(any(d["key"] == "pph21" for d in preview["deductions"]))
        self.assertEqual(preview["net"], preview["gross"] - preview["deductions_total"])

    def test_daily_preview_uses_work_days(self):
        employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            employee_id="E-D",
            full_name="Daily Staff",
            salary_scheme=Employee.SalaryScheme.DAILY,
            base_salary=Decimal("200000"),
            allowance_meal=Decimal("25000"),
            allowance_transport=Decimal("50000"),
        )
        preview = build_salary_preview(employee, tenant=self.tenant, work_days=22)
        self.assertEqual(preview["gross"], Decimal("6050000.00"))
        self.assertTrue(preview["is_daily"])
