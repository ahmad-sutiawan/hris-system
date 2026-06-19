from datetime import datetime, time
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.attendance.models import AttendanceCode, AttendanceRecord, OvertimeType
from apps.attendance.services.overtime_workflow import approve_overtime_request, submit_overtime_request
from apps.attendance.services.timesheet import recalculate_daily_timesheet
from apps.attendance.services.timesheet_engine import calculate_timesheet_metrics
from apps.core.models import FeatureFlag, Plant, Tenant, User
from apps.employees.models import Employee
from apps.organization.models import Department
from apps.payroll.models import PayrollRun, Payslip
from apps.payroll.services.calculator import calc_ot_pay, calc_period_base
from apps.payroll.services.payroll_run import calculate_payroll_run
from apps.shifts.models import Shift, ShiftAssignment


class FlexibleHoursTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Flex Co", slug="flexco")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.dept = Department.objects.create(
            tenant=self.tenant, plant=self.plant, code="D1", name="Prod"
        )
        self.hr = User.objects.create_user(
            username="hr-flex",
            password="TestPassword123!",
            tenant=self.tenant,
            role=User.Role.HR,
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            employee_id="E-FLEX",
            full_name="Flex Worker",
            base_salary=Decimal("5000000"),
            tax_status="TK/0",
        )
        self.shift = Shift.objects.create(
            tenant=self.tenant,
            name="Pagi",
            code="PAGI",
            scheduled_check_in=time(7, 0),
            scheduled_check_out=time(15, 0),
            break_minutes=60,
            schedule_working_hours=Decimal("8"),
        )
        AttendanceCode.objects.create(tenant=self.tenant, code="H", label="Hadir")
        AttendanceCode.objects.create(tenant=self.tenant, code="A", label="Alpha")
        self.work_date = timezone.localdate()
        self.tz = timezone.get_current_timezone()
        self.overtime_type = OvertimeType.objects.create(
            tenant=self.tenant,
            code="OT-HK-1",
            name="Lembur Hari Kerja Jam I",
            day_category=OvertimeType.DayCategory.WORKDAY,
            hour_from=1,
            hour_to=1,
            multiplier=Decimal("1.5"),
        )

    def _punch(self, check_in, check_out):
        AttendanceRecord.objects.update_or_create(
            employee=self.employee,
            work_date=self.work_date,
            defaults={
                "tenant": self.tenant,
                "plant": self.plant,
                "check_in": timezone.make_aware(
                    datetime.combine(self.work_date, check_in), self.tz
                ),
                "check_out": timezone.make_aware(
                    datetime.combine(self.work_date, check_out), self.tz
                ),
            },
        )

    def test_long_shift_schedule_from_assignment_window(self):
        ShiftAssignment.objects.create(
            tenant=self.tenant,
            employee=self.employee,
            shift=self.shift,
            work_date=self.work_date,
            scheduled_check_in=time(7, 0),
            scheduled_check_out=time(19, 0),
        )
        self._punch(time(7, 0), time(19, 0))
        ts = recalculate_daily_timesheet(self.employee, self.work_date)
        self.assertEqual(ts.schedule_working_hours, Decimal("11.00"))
        self.assertEqual(ts.actual_working_hours, Decimal("11.00"))
        self.assertEqual(ts.paid_working_hours, Decimal("11.00"))
        self.assertEqual(ts.ot_after_minutes, 0)

    def test_long_shift_ot_after_requires_approval(self):
        ShiftAssignment.objects.create(
            tenant=self.tenant,
            employee=self.employee,
            shift=self.shift,
            work_date=self.work_date,
            scheduled_check_in=time(7, 0),
            scheduled_check_out=time(19, 0),
        )
        self._punch(time(7, 0), time(20, 0))
        ts = recalculate_daily_timesheet(self.employee, self.work_date)
        self.assertEqual(ts.ot_after_minutes, 0)

        req = submit_overtime_request(
            employee=self.employee,
            work_date=self.work_date,
            overtime_type=self.overtime_type,
            ot_after_minutes=120,
            reason="Closing line",
        )
        approve_overtime_request(req, self.hr)
        ts = recalculate_daily_timesheet(self.employee, self.work_date)
        self.assertEqual(ts.ot_after_minutes, 60)
        self.assertGreater(ts.paid_working_hours, Decimal("11.00"))

    def test_ot_before_disabled_by_hr_policy(self):
        """HR policy (Jun 2026): OT after shift only — ot_before ignored."""
        ShiftAssignment.objects.create(
            tenant=self.tenant,
            employee=self.employee,
            shift=self.shift,
            work_date=self.work_date,
            scheduled_check_in=time(7, 0),
            scheduled_check_out=time(15, 0),
        )
        self._punch(time(6, 0), time(16, 0))
        ts = recalculate_daily_timesheet(self.employee, self.work_date)
        self.assertEqual(ts.ot_before_minutes, 0)

        req = submit_overtime_request(
            employee=self.employee,
            work_date=self.work_date,
            overtime_type=self.overtime_type,
            ot_before_minutes=60,
            ot_after_minutes=30,
            reason="Prep line",
        )
        self.assertEqual(req.ot_before_minutes, 0)
        approve_overtime_request(req, self.hr)
        ts = recalculate_daily_timesheet(self.employee, self.work_date)
        self.assertEqual(ts.ot_before_minutes, 0)
        self.assertGreater(ts.ot_after_minutes, 0)

    def test_engine_derives_schedule_when_none(self):
        metrics = calculate_timesheet_metrics(
            work_date=self.work_date,
            scheduled_check_in=time(7, 0),
            scheduled_check_out=time(19, 0),
            check_in=timezone.make_aware(
                datetime.combine(self.work_date, time(7, 0)), self.tz
            ),
            check_out=timezone.make_aware(
                datetime.combine(self.work_date, time(19, 0)), self.tz
            ),
            break_minutes=60,
            schedule_working_hours=None,
        )
        self.assertEqual(metrics["schedule_working_hours"], Decimal("11.00"))


class FlexiblePayrollTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Pay Co", slug="payco")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.dept = Department.objects.create(
            tenant=self.tenant, plant=self.plant, code="D1", name="Prod"
        )
        self.hr = User.objects.create_user(
            username="hr-pay",
            password="TestPassword123!",
            tenant=self.tenant,
            role=User.Role.HR,
        )
        self.monthly_employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            employee_id="E-MON",
            full_name="Monthly Worker",
            base_salary=Decimal("4400000"),
            tax_status="TK/0",
            salary_scheme=Employee.SalaryScheme.MONTHLY,
        )
        self.daily_employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            employee_id="E-DAY",
            full_name="Daily Worker",
            base_salary=Decimal("200000"),
            tax_status="TK/0",
            salary_scheme=Employee.SalaryScheme.DAILY,
        )
        self.shift = Shift.objects.create(
            tenant=self.tenant,
            name="Pagi",
            code="PAGI",
            scheduled_check_in=time(7, 0),
            scheduled_check_out=time(15, 0),
        )
        AttendanceCode.objects.create(tenant=self.tenant, code="H", label="Hadir")
        self.work_date = timezone.localdate()
        self.tz = timezone.get_current_timezone()

    def test_daily_scheme_base_from_present_days(self):
        base = calc_period_base(self.daily_employee, present_days=3)
        self.assertEqual(base, Decimal("600000"))

    def test_payroll_includes_ot_before_and_after(self):
        from apps.attendance.models import DailyTimesheet, OvertimeRequest, OvertimeType

        ot_type = OvertimeType.objects.create(
            tenant=self.tenant,
            code="OT-HK-1",
            name="Lembur Hari Kerja Jam I",
            day_category=OvertimeType.DayCategory.WORKDAY,
            hour_from=1,
            hour_to=1,
            multiplier=Decimal("1.5"),
        )
        OvertimeRequest.objects.create(
            tenant=self.tenant,
            employee=self.monthly_employee,
            work_date=self.work_date,
            overtime_type=ot_type,
            ot_before_minutes=60,
            ot_after_minutes=120,
            status=OvertimeRequest.Status.APPROVED,
        )
        DailyTimesheet.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee=self.monthly_employee,
            work_date=self.work_date,
            check_in=timezone.now(),
            ot_before_minutes=60,
            ot_after_minutes=120,
            paid_working_hours=Decimal("8"),
        )
        run = PayrollRun.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            period_start=self.work_date.replace(day=1),
            period_end=self.work_date,
        )
        calculate_payroll_run(run)
        slip = Payslip.objects.get(payroll_run=run, employee=self.monthly_employee)
        ot_before_pay = calc_ot_pay(self.monthly_employee, 60, multiplier=Decimal("1.5"))
        ot_after_pay = calc_ot_pay(self.monthly_employee, 120, multiplier=Decimal("1.5"))
        self.assertIn("ot_before", slip.earnings_breakdown)
        self.assertEqual(slip.earnings_breakdown["ot_before"], str(ot_before_pay))
        self.assertEqual(slip.earnings_breakdown["ot_after"], str(ot_after_pay))
        self.assertEqual(
            slip.gross_amount,
            Decimal("4400000") + ot_before_pay + ot_after_pay,
        )

    def test_payroll_daily_worker_present_days(self):
        from apps.attendance.models import DailyTimesheet

        for day in (1, 2, 3):
            work_date = self.work_date.replace(day=day)
            DailyTimesheet.objects.create(
                tenant=self.tenant,
                plant=self.plant,
                    employee=self.daily_employee,
                work_date=work_date,
                check_in=timezone.make_aware(
                    datetime.combine(work_date, time(7, 0)), self.tz
                ),
                paid_working_hours=Decimal("8"),
            )
        run = PayrollRun.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            period_start=self.work_date.replace(day=1),
            period_end=self.work_date.replace(day=3),
        )
        calculate_payroll_run(run)
        slip = Payslip.objects.get(payroll_run=run, employee=self.daily_employee)
        self.assertEqual(slip.earnings_breakdown["base_salary"], "600000.00")
