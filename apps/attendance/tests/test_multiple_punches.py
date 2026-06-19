from datetime import datetime, time, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.attendance.models import AttendancePunch, AttendanceRecord
from apps.attendance.services.photo import decode_selfie
from apps.attendance.services.punch import clock_in, clock_out
from apps.attendance.tests.test_punch_photo import _sample_photo_data_url
from apps.core.models import Plant, Tenant
from apps.employees.models import Employee


class MultiplePunchTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="multi-punch", name="Multi Punch Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant")
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="MP-001",
            full_name="Multi Puncher",
            join_date=timezone.localdate(),
        )
        self.photo = decode_selfie(_sample_photo_data_url())
        self.tz = timezone.get_current_timezone()
        self.work_date = timezone.localdate()

    def _at(self, hour: int, minute: int = 0) -> datetime:
        return timezone.make_aware(datetime.combine(self.work_date, time(hour, minute)), self.tz)

    def test_second_clock_in_keeps_both_punches_and_existing_clock_out(self):
        morning = self._at(7, 30)
        afternoon = self._at(13, 15)
        evening = self._at(17, 0)

        clock_in(self.employee, when=morning, photo=self.photo)
        clock_out(self.employee, when=evening, photo=self.photo)
        clock_in(self.employee, when=afternoon, photo=self.photo)

        record = AttendanceRecord.objects.get(employee=self.employee, work_date=self.work_date)
        punches = list(record.punches.order_by("punched_at", "pk"))

        self.assertEqual(len(punches), 3)
        self.assertEqual(punches[0].punch_type, AttendancePunch.PunchType.IN)
        self.assertEqual(punches[1].punch_type, AttendancePunch.PunchType.OUT)
        self.assertEqual(punches[2].punch_type, AttendancePunch.PunchType.IN)
        self.assertEqual(timezone.localtime(record.check_in), morning)
        self.assertEqual(timezone.localtime(record.check_out), evening)

    def test_multiple_clock_outs_are_all_recorded(self):
        first = self._at(12, 0)
        second = self._at(17, 30)

        clock_in(self.employee, when=self._at(7, 0), photo=self.photo)
        clock_out(self.employee, when=first, photo=self.photo)
        clock_out(self.employee, when=second, photo=self.photo)

        record = AttendanceRecord.objects.get(employee=self.employee, work_date=self.work_date)
        outs = record.punches.filter(punch_type=AttendancePunch.PunchType.OUT).order_by("punched_at")

        self.assertEqual(outs.count(), 2)
        self.assertEqual(timezone.localtime(record.check_out), second)

    def test_re_clock_in_does_not_clear_clock_out(self):
        clock_in(self.employee, when=self._at(8, 0), photo=self.photo)
        clock_out(self.employee, when=self._at(17, 0), photo=self.photo)
        clock_in(self.employee, when=self._at(13, 0), photo=self.photo)

        record = AttendanceRecord.objects.get(employee=self.employee, work_date=self.work_date)
        self.assertIsNotNone(record.check_out)
        self.assertEqual(record.punches.filter(punch_type=AttendancePunch.PunchType.IN).count(), 2)
