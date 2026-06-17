from datetime import datetime, time, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.attendance.models import OvertimeRequest, OvertimeType
from apps.attendance.services.overtime_compensation import (
    OT_LEAVE_MINUTES_PER_DAY,
    build_compensation_preview,
    get_or_create_overtime_leave_type,
    overtime_minutes_to_leave_days,
)
from apps.attendance.services.overtime_workflow import approve_overtime_request, submit_overtime_request
from apps.attendance.services.punch import clock_in, clock_out
from apps.attendance.services.photo import decode_selfie
from apps.attendance.tests.test_punch_photo import _sample_photo_data_url
from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.leave.models import LeaveBalance, LeaveRequest
from apps.leave.services.leave_workflow import approve_leave_request, submit_leave_request
from apps.organization.models import Department
from apps.shifts.models import Shift, ShiftAssignment


class OvertimeCompensationTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="OT Comp Co", slug="otcomp")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant")
        self.dept = Department.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="D1",
            name="Prod",
        )
        self.hr = User.objects.create_user(
            username="hr-otcomp",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.HR,
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            employee_id="E-OTC",
            full_name="OT Comp Worker",
            salary_scheme=Employee.SalaryScheme.DAILY,
            base_salary=Decimal("200000"),
        )
        self.shift = Shift.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            name="Pagi",
            code="PAGI",
            scheduled_check_in=time(7, 0),
            scheduled_check_out=time(15, 0),
        )
        self.work_date = timezone.localdate()
        self.overtime_type = OvertimeType.objects.create(
            tenant=self.tenant,
            code="OT-HK-1",
            name="Lembur Hari Kerja Jam I",
            day_category=OvertimeType.DayCategory.WORKDAY,
            hour_from=1,
            hour_to=1,
            multiplier=Decimal("1.5"),
        )
        ShiftAssignment.objects.create(
            tenant=self.tenant,
            employee=self.employee,
            shift=self.shift,
            work_date=self.work_date,
            scheduled_check_in=time(7, 0),
            scheduled_check_out=time(15, 0),
        )
        self.photo = decode_selfie(_sample_photo_data_url())
        tz = timezone.get_current_timezone()
        clock_in(
            self.employee,
            when=timezone.make_aware(datetime.combine(self.work_date, time(7, 0)), tz),
            photo=self.photo,
        )
        clock_out(
            self.employee,
            when=timezone.make_aware(datetime.combine(self.work_date, time(17, 0)), tz),
            photo=self.photo,
        )

    def test_leave_days_conversion(self):
        self.assertEqual(overtime_minutes_to_leave_days(240), Decimal("0.50"))
        self.assertEqual(
            overtime_minutes_to_leave_days(OT_LEAVE_MINUTES_PER_DAY),
            Decimal("1.00"),
        )

    def test_preview_uses_daily_hourly_rate(self):
        preview = build_compensation_preview(
            self.employee,
            ot_before_minutes=0,
            ot_after_minutes=120,
            overtime_type=self.overtime_type,
        )
        self.assertIn("Gaji harian", preview["grade_label"])
        self.assertIn("Rp", preview["cash_amount"])

    def test_approve_leave_mode_credits_balance(self):
        req = submit_overtime_request(
            employee=self.employee,
            work_date=self.work_date,
            overtime_type=self.overtime_type,
            ot_after_minutes=120,
            compensation_mode=OvertimeRequest.CompensationMode.LEAVE,
        )
        approve_overtime_request(req, self.hr)
        req.refresh_from_db()
        self.assertEqual(req.leave_days_credited, Decimal("0.25"))

        balance = LeaveBalance.objects.get(
            employee=self.employee,
            leave_type__code="CL",
            year=self.work_date.year,
        )
        self.assertEqual(balance.remaining, Decimal("0.25"))
        self.assertEqual(balance.accrued, Decimal("0.25"))

    def test_cl_balance_used_when_taking_leave(self):
        cl_type = get_or_create_overtime_leave_type(self.tenant)
        LeaveBalance.objects.create(
            tenant=self.tenant,
            employee=self.employee,
            leave_type=cl_type,
            year=self.work_date.year,
            opening_balance=Decimal("0"),
            accrued=Decimal("1"),
            used=Decimal("0"),
            pending=Decimal("0"),
            remaining=Decimal("1"),
        )
        leave_req = submit_leave_request(
            employee=self.employee,
            leave_type=cl_type,
            start_date=self.work_date + timedelta(days=10),
            end_date=self.work_date + timedelta(days=10),
            reason="Pakai cuti lembur",
        )
        balance = LeaveBalance.objects.get(
            employee=self.employee,
            leave_type=cl_type,
            year=self.work_date.year,
        )
        self.assertEqual(balance.remaining, Decimal("0"))
        self.assertEqual(balance.pending, Decimal("1"))

        approve_leave_request(leave_req, self.hr)
        balance.refresh_from_db()
        self.assertEqual(balance.used, Decimal("1"))
        self.assertEqual(balance.pending, Decimal("0"))
        self.assertEqual(leave_req.status, LeaveRequest.Status.APPROVED)
