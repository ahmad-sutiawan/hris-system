from datetime import date, datetime, time
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.attendance.models import OvertimeRequest, OvertimeType
from apps.attendance.services.overtime_workflow import (
    OvertimeError,
    approve_overtime_request,
    submit_overtime_request,
)
from apps.attendance.services.punch import clock_in, clock_out
from apps.attendance.services.timesheet import recalculate_daily_timesheet
from apps.attendance.tests.test_punch_photo import _sample_photo_data_url
from apps.attendance.services.photo import decode_selfie
from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.organization.models import Department
from apps.shifts.models import Shift, ShiftAssignment


class OvertimeApprovalGateTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="OT Co", slug="otco")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant")
        self.dept = Department.objects.create(
            tenant=self.tenant, plant=self.plant, code="D1", name="Prod"
        )
        self.hr = User.objects.create_user(
            username="hr-ot",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.HR,
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            employee_id="E-OT",
            full_name="OT Worker",
            base_salary=Decimal("5000000"),
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

    def test_ot_zero_without_approval(self):
        ts = recalculate_daily_timesheet(self.employee, self.work_date)
        self.assertEqual(ts.ot_after_minutes, 0)

    def test_ot_counts_after_approval(self):
        req = submit_overtime_request(
            employee=self.employee,
            work_date=self.work_date,
            overtime_type=self.overtime_type,
            ot_after_minutes=120,
            reason="Closing line",
        )
        approve_overtime_request(req, self.hr)
        ts = recalculate_daily_timesheet(self.employee, self.work_date)
        self.assertEqual(ts.ot_after_minutes, 120)
        req.refresh_from_db()
        self.assertEqual(req.status, OvertimeRequest.Status.APPROVED)

    def test_submit_requires_minutes(self):
        with self.assertRaises(OvertimeError):
            submit_overtime_request(
                employee=self.employee,
                work_date=self.work_date,
                overtime_type=self.overtime_type,
                ot_before_minutes=0,
                ot_after_minutes=0,
            )

    def test_submit_requires_overtime_type(self):
        with self.assertRaises(OvertimeError):
            submit_overtime_request(
                employee=self.employee,
                work_date=self.work_date,
                ot_after_minutes=60,
            )
