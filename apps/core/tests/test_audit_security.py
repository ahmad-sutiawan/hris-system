from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.db import connection

from apps.core.management.commands.archive_audit_logs import Command as ArchiveCommand
from apps.core.models import AuditLog, Plant, Tenant, User
from apps.core.services.audit import log_audit, verify_integrity
from apps.employees.models import Employee
from apps.organization.models import Department
from apps.payroll.models import PayrollRun
from apps.payroll.services.payroll_run import calculate_payroll_run


class AuditSecurityTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="audit-sec", name="Audit Sec")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant")
        self.dept = Department.objects.create(
            tenant=self.tenant, plant=self.plant, code="D1", name="Prod"
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            employee_id="E-AUD",
            full_name="Audit Worker",
            base_salary=Decimal("5000000"),
        )

    def test_audit_log_is_append_only(self):
        self.employee.full_name = "Changed"
        self.employee.save()
        log = AuditLog.objects.latest("created_at")
        with self.assertRaises(PermissionDenied):
            log.object_repr = "tampered"
            log.save()
        with self.assertRaises(PermissionDenied):
            log.delete()

    def test_integrity_hash_verifies(self):
        log_audit(AuditLog.Action.CREATE, self.employee)
        log = AuditLog.objects.latest("created_at")
        self.assertTrue(log.integrity_hash)
        self.assertTrue(verify_integrity(log))

    def test_sensitive_salary_masked_in_changes(self):
        self.employee.base_salary = Decimal("6000000")
        self.employee.save()
        log = AuditLog.objects.filter(
            model_name="employees.employee",
            action=AuditLog.Action.UPDATE,
        ).latest("created_at")
        self.assertEqual(log.changes["base_salary"], "***")


class PayrollQueryBudgetTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="perf", name="Perf Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant")
        self.dept = Department.objects.create(
            tenant=self.tenant, plant=self.plant, code="D1", name="Prod"
        )
        for idx in range(8):
            Employee.objects.create(
                tenant=self.tenant,
                plant=self.plant,
                department=self.dept,
                employee_id=f"E-{idx}",
                full_name=f"Worker {idx}",
                base_salary=Decimal("4000000"),
                salary_scheme=Employee.SalaryScheme.MONTHLY,
            )
        self.run = PayrollRun.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            period_start="2026-06-01",
            period_end="2026-06-30",
        )

    def test_payroll_calculate_query_budget(self):
        with CaptureQueriesContext(connection) as ctx:
            calculate_payroll_run(self.run)
        # Bulk aggregation: tidak boleh N+1 per karyawan (8 workers → well under 8× timesheet queries)
        self.assertLessEqual(len(ctx.captured_queries), 40)

    @override_settings(HRIS_AUDIT_RETENTION_DAYS=0)
    def test_archive_audit_logs_dry_run(self):
        before = AuditLog.objects.count()
        cmd = ArchiveCommand()
        cmd.handle(days=0, batch_size=100, dry_run=True, tenant_slug="perf")
        self.assertEqual(AuditLog.objects.count(), before)
