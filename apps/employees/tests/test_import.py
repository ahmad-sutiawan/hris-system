from decimal import Decimal
from io import StringIO

from django.test import TestCase

from apps.core.models import Plant, Tenant
from apps.employees.models import Employee
from apps.core.xlsx_io import XLSX_CONTENT_TYPE, read_xlsx_rows, write_xlsx
from apps.employees.services.import_csv import (
    IMPORT_HEADERS,
    import_employees_csv,
    import_employees_xlsx,
    template_xlsx,
)
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
        headers, _ = read_xlsx_rows(template_xlsx())
        self.assertIn("employee_id", headers)

    def test_import_creates_employee(self):
        result = import_employees_xlsx(self.tenant, template_xlsx())
        self.assertEqual(result["created"], 1)

    def test_import_reports_row_progress(self):
        calls = []
        result = import_employees_xlsx(
            self.tenant,
            template_xlsx(),
            on_progress=lambda processed, total, created, updated: calls.append(
                (processed, total, created, updated)
            ),
        )
        self.assertEqual(result["created"], 1)
        self.assertEqual(calls[0], (0, 1, 0, 0))
        self.assertEqual(calls[-1], (1, 1, 1, 0))
        employee = Employee.objects.get(tenant=self.tenant)
        self.assertEqual(employee.salary_scheme, Employee.SalaryScheme.DAILY)
        self.assertEqual(employee.base_salary, Decimal("200000"))
        self.assertEqual(employee.allowance_meal, Decimal("25000"))
        self.assertEqual(employee.bpjs_kesehatan_number, "0001234567890")

    def _row(self, employee_id, full_name, nik, **overrides):
        base = {
            "employee_id": employee_id,
            "full_name": full_name,
            "nik": nik,
            "email": f"{employee_id}@demo.local",
            "phone": "08123456789",
            "plant_code": "PLT01",
            "department_code": "PROD",
            "job_code": "OPR",
            "join_date": "2026-01-15",
            "status": "permanent",
            "base_salary": "100000",
            "allowance_transport": "0",
            "tax_status": "TK/0",
            "bank_name": "BCA",
            "bank_account_number": "123",
            "bank_account_name": full_name,
            "npwp": "123456789012345",
        }
        base.update(overrides)
        return base

    def _xlsx(self, rows):
        return write_xlsx(IMPORT_HEADERS, [[row.get(header, "") for header in IMPORT_HEADERS] for row in rows])

    def test_incremental_import_keeps_existing_and_adds_new(self):
        first = import_employees_xlsx(
            self.tenant,
            self._xlsx([self._row("E0", "Budi Santoso", "3201010101900001", base_salary="100000")]),
        )
        self.assertEqual(first["created"], 1)
        existing = Employee.objects.get(tenant=self.tenant, employee_id="E0")
        existing.base_salary = Decimal("999")
        existing.email = "old@x.test"
        existing.save()

        rows = [self._row("E0", "Budi Santoso", "3201010101900001", base_salary="1", email="new@x.test")]
        for index in range(1, 11):
            rows.append(
                self._row(f"EMP{index:02d}", f"Karyawan {index}", f"3201010101901{index:03d}")
            )
        rows.append(self._row("EMP-DUP", "Karyawan 1", "3201010101901001"))
        rows.append(self._row("EMP-NAME", "Karyawan 1", "3201010101901999"))

        result = import_employees_xlsx(self.tenant, self._xlsx(rows))

        self.assertEqual(result["created"], 11)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["rejected"], 2)
        self.assertEqual(Employee.objects.filter(tenant=self.tenant).count(), 12)
        existing.refresh_from_db()
        self.assertEqual(existing.base_salary, Decimal("999"))
        self.assertEqual(existing.email, "old@x.test")
        self.assertTrue(Employee.objects.filter(tenant=self.tenant, employee_id="EMP-NAME").exists())
        self.assertFalse(Employee.objects.filter(tenant=self.tenant, employee_id="EMP-DUP").exists())
        self.assertTrue(any("NIK dan nama sudah terdaftar" in err for err in result["errors"]))


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
