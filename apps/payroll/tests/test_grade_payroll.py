from datetime import datetime, time, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.attendance.models import DailyTimesheet, OvertimeRequest, OvertimeType
from apps.core.models import Plant, Tenant
from apps.employees.models import Employee
from apps.organization.models import Department, EmployeeGrade
from apps.payroll.models import PayrollRun, Payslip
from apps.payroll.services.calculator import (
    aggregate_overtime_pay,
    calc_ot_pay,
    calc_period_base,
    daily_rate,
    hourly_rate,
)
from apps.payroll.services.payroll_run import calculate_payroll_run


class GradePayrollTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Steel Co", slug="steelco")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant Baja")
        self.dept = Department.objects.create(
            tenant=self.tenant, plant=self.plant, code="PROD", name="Produksi"
        )
        self.grade_g2 = EmployeeGrade.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="G2",
            name="Operator",
            daily_wage=Decimal("200000"),
        )
        self.grade_g4 = EmployeeGrade.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="G4",
            name="Foreman",
            daily_wage=Decimal("250000"),
        )
        self.worker_g2 = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            employee_grade=self.grade_g2,
            employee_id="E-G2",
            full_name="Operator G2",
            salary_scheme=Employee.SalaryScheme.DAILY,
            base_salary=Decimal("180000"),
            tax_status="TK/0",
        )
        self.worker_g4 = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            employee_grade=self.grade_g4,
            employee_id="E-G4",
            full_name="Foreman G4",
            salary_scheme=Employee.SalaryScheme.DAILY,
            base_salary=Decimal("230000"),
            tax_status="TK/0",
        )
        self.ot_hk1 = OvertimeType.objects.create(
            tenant=self.tenant,
            code="OT-HK-1",
            name="Lembur Hari Kerja Jam I",
            day_category=OvertimeType.DayCategory.WORKDAY,
            hour_from=1,
            hour_to=1,
            multiplier=Decimal("1.5"),
        )
        self.ot_hk2 = OvertimeType.objects.create(
            tenant=self.tenant,
            code="OT-HK-2",
            name="Lembur Hari Kerja Jam II+",
            day_category=OvertimeType.DayCategory.WORKDAY,
            hour_from=2,
            multiplier=Decimal("2"),
        )
        self.work_date = timezone.localdate()
        self.tz = timezone.get_current_timezone()

    def test_daily_rate_from_grade_not_base_salary(self):
        self.assertEqual(daily_rate(self.worker_g2), Decimal("200000"))
        self.assertEqual(daily_rate(self.worker_g4), Decimal("250000"))
        self.assertEqual(hourly_rate(self.worker_g2), Decimal("25000"))

    def test_period_base_uses_grade_daily_wage(self):
        base = calc_period_base(self.worker_g2, present_days=5)
        self.assertEqual(base, Decimal("1000000"))

    def test_same_ot_minutes_different_grade_different_pay(self):
        pay_g2 = calc_ot_pay(self.worker_g2, 120, multiplier=Decimal("1.5"))
        pay_g4 = calc_ot_pay(self.worker_g4, 120, multiplier=Decimal("1.5"))
        self.assertGreater(pay_g4, pay_g2)
        self.assertEqual(pay_g2, Decimal("75000"))
        self.assertEqual(pay_g4, Decimal("93750"))

    def test_overtime_pay_uses_overtime_type_multiplier(self):
        for day_offset, ot_type, minutes in (
            (0, self.ot_hk1, 60),
            (1, self.ot_hk2, 120),
        ):
            work_date = self.work_date - timedelta(days=day_offset)
            OvertimeRequest.objects.create(
                tenant=self.tenant,
                employee=self.worker_g2,
                work_date=work_date,
                overtime_type=ot_type,
                ot_after_minutes=minutes,
                status=OvertimeRequest.Status.APPROVED,
            )
            DailyTimesheet.objects.create(
                tenant=self.tenant,
                plant=self.plant,
                employee=self.worker_g2,
                work_date=work_date,
                check_in=timezone.make_aware(
                    datetime.combine(work_date, time(7, 0)), self.tz
                ),
                ot_after_minutes=minutes,
                paid_working_hours=Decimal("8"),
            )

        period_start = self.work_date - timedelta(days=1)
        total, detail = aggregate_overtime_pay(self.worker_g2, period_start, self.work_date)
        expected_hk1 = calc_ot_pay(self.worker_g2, 60, multiplier=Decimal("1.5"))
        expected_hk2 = calc_ot_pay(self.worker_g2, 120, multiplier=Decimal("2"))
        self.assertEqual(total, expected_hk1 + expected_hk2)
        self.assertEqual(detail["by_type"]["OT-HK-1"], expected_hk1)
        self.assertEqual(detail["by_type"]["OT-HK-2"], expected_hk2)

    def test_payroll_run_breakdown_by_grade_and_ot_type(self):
        OvertimeRequest.objects.create(
            tenant=self.tenant,
            employee=self.worker_g2,
            work_date=self.work_date,
            overtime_type=self.ot_hk2,
            ot_after_minutes=120,
            status=OvertimeRequest.Status.APPROVED,
        )
        DailyTimesheet.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee=self.worker_g2,
            work_date=self.work_date,
            check_in=timezone.make_aware(
                datetime.combine(self.work_date, time(7, 0)), self.tz
            ),
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
        slip = Payslip.objects.get(payroll_run=run, employee=self.worker_g2)
        self.assertEqual(slip.earnings_breakdown["grade_code"], "G2")
        self.assertEqual(slip.earnings_breakdown["daily_wage"], "200000.00")
        self.assertIn("OT-HK-2", slip.earnings_breakdown["ot_by_type"])
        ot_pay = calc_ot_pay(self.worker_g2, 120, multiplier=Decimal("2"))
        self.assertEqual(slip.earnings_breakdown["ot_by_type"]["OT-HK-2"], str(ot_pay))
