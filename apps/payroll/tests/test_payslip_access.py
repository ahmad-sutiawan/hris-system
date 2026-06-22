"""Payslip visibility and payroll finalize guards."""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.payroll.models import PayrollRun, Payslip
from apps.payroll.services.payroll_run import PayrollError, calculate_payroll_run, finalize_payroll_run


class PayslipAccessTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="slip-access", name="Slip Access Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant")
        self.user = User.objects.create_user(
            username="slip-emp",
            password="E-001",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.EMPLOYEE,
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="E-001",
            full_name="Slip Employee",
            user=self.user,
            join_date=date(2024, 1, 1),
            base_salary=Decimal("5000000"),
        )
        self.run = PayrollRun.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
        )
        calculate_payroll_run(self.run)
        self.payslip = Payslip.objects.get(payroll_run=self.run, employee=self.employee)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_employee_cannot_list_review_payslips(self):
        response = self.client.get("/api/v1/payslips/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data.get("results", response.data)), 0)

    def test_employee_sees_payslip_after_finalize(self):
        finalize_payroll_run(self.run)
        response = self.client.get("/api/v1/payslips/")
        self.assertEqual(response.status_code, 200)
        rows = response.data.get("results", response.data)
        self.assertEqual(len(rows), 1)

    def test_finalize_requires_review_status(self):
        draft = PayrollRun.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
        )
        with self.assertRaises(PayrollError):
            finalize_payroll_run(draft)
