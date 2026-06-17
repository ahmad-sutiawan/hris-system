from decimal import Decimal

from django.test import TestCase

from apps.core.models import Plant, Tenant
from apps.employees.models import Employee
from apps.organization.models import Department
from apps.payroll.models import Pph21TerBracket, Pph21TerCategory
from apps.payroll.services.calculator import calc_pph21, calc_period_base, daily_rate
from apps.payroll.services.ter import lookup_ter_rate, seed_ter_master


class PayrollSalaryTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Pay Co", slug="payco")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant")
        self.dept = Department.objects.create(
            tenant=self.tenant, plant=self.plant, code="D1", name="Prod"
        )
        seed_ter_master(self.tenant)
        self.worker = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            employee_id="E-DAILY",
            full_name="Daily Worker",
            salary_scheme=Employee.SalaryScheme.DAILY,
            base_salary=Decimal("200000"),
            tax_status="TK/0",
        )

    def test_daily_rate_from_base_salary(self):
        self.assertEqual(daily_rate(self.worker), Decimal("200000"))

    def test_period_base_uses_daily_wage(self):
        base = calc_period_base(self.worker, present_days=5)
        self.assertEqual(base, Decimal("1000000"))

    def test_ter_lookup_category_a(self):
        rate = lookup_ter_rate(
            tenant=self.tenant,
            gross=Decimal("7000000"),
            ptkp_code="TK/0",
        )
        self.assertEqual(rate, Decimal("0.0125"))

    def test_calc_pph21_uses_ter_master(self):
        gross = Decimal("7000000")
        tax = calc_pph21(gross, self.worker)
        self.assertEqual(tax, Decimal("87500.00"))

    def test_calc_pph21_skipped_when_no_ptkp(self):
        self.worker.tax_status = ""
        self.worker.save(update_fields=["tax_status"])
        self.assertEqual(calc_pph21(Decimal("7000000"), self.worker), Decimal("0"))

    def test_calc_pph21_skipped_when_disabled(self):
        self.worker.pph21_deduct = False
        self.worker.save(update_fields=["pph21_deduct"])
        self.assertEqual(calc_pph21(Decimal("7000000"), self.worker), Decimal("0"))

    def test_ter_master_seeded_all_categories(self):
        self.assertEqual(Pph21TerCategory.objects.filter(tenant=self.tenant).count(), 3)
        self.assertEqual(
            Pph21TerBracket.objects.filter(tenant=self.tenant, category__code="A").count(),
            44,
        )
