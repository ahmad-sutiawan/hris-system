from datetime import date, datetime, time
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.attendance.services.timesheet_engine import calculate_timesheet_metrics
from apps.attendance.services.timesheet import recalculate_daily_timesheet
from apps.attendance.services.punch import clock_in, clock_out
from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.leave.services.leave_workflow import approve_leave_request, submit_leave_request
from apps.leave.models import LeaveType
from apps.organization.models import Department
from apps.payroll.services.payroll_run import calculate_payroll_run, finalize_payroll_run
from apps.payroll.models import PayrollRun
from apps.shifts.models import Shift, ShiftAssignment


class TimesheetEngineTests(TestCase):
    def test_on_time_full_day(self):
        metrics = calculate_timesheet_metrics(
            work_date=date(2026, 6, 10),
            scheduled_check_in=time(7, 0),
            scheduled_check_out=time(15, 0),
            check_in=timezone.make_aware(datetime(2026, 6, 10, 7, 0)),
            check_out=timezone.make_aware(datetime(2026, 6, 10, 15, 0)),
            break_minutes=60,
            grace_period_minutes=15,
            schedule_working_hours=Decimal("8"),
        )
        self.assertEqual(metrics["late_in_minutes"], 0)
        self.assertEqual(metrics["actual_working_hours"], Decimal("7.00"))
        self.assertGreaterEqual(metrics["paid_working_hours"], Decimal("7"))


class EndToEndFlowTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="T", slug="t")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.dept = Department.objects.create(
            tenant=self.tenant, plant=self.plant, code="D1", name="Prod"
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            employee_id="E001",
            full_name="Test Employee",
            base_salary=Decimal("5000000"),
            tax_status="TK/0",
        )
        self.shift = Shift.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            name="Pagi",
            code="PAGI",
            scheduled_check_in=time(7, 0),
            scheduled_check_out=time(15, 0),
            break_minutes=60,
            schedule_working_hours=Decimal("8"),
        )
        self.leave_type = LeaveType.objects.create(
            tenant=self.tenant, code="CT", name="Cuti Tahunan", default_quota_days=12
        )
        from apps.attendance.models import AttendanceCode

        AttendanceCode.objects.create(
            tenant=self.tenant, code="H", label="Hadir"
        )
        AttendanceCode.objects.create(
            tenant=self.tenant, code="C", label="Cuti"
        )
        AttendanceCode.objects.create(
            tenant=self.tenant, code="A", label="Alpha"
        )

    def test_punch_creates_timesheet(self):
        today = timezone.localdate()
        ShiftAssignment.objects.create(
            tenant=self.tenant,
            employee=self.employee,
            shift=self.shift,
            work_date=today,
            scheduled_check_in=time(7, 0),
            scheduled_check_out=time(15, 0),
        )
        clock_in(self.employee)
        clock_out(self.employee)
        ts = recalculate_daily_timesheet(self.employee, today)
        self.assertIsNotNone(ts.check_in)
        self.assertIsNotNone(ts.check_out)

    def test_payroll_run(self):
        today = timezone.localdate()
        run = PayrollRun.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            period_start=today.replace(day=1),
            period_end=today,
        )
        calculate_payroll_run(run)
        run.refresh_from_db()
        self.assertEqual(run.status, PayrollRun.Status.REVIEW)
        finalize_payroll_run(run)
        run.refresh_from_db()
        self.assertEqual(run.status, PayrollRun.Status.FINALIZED)
