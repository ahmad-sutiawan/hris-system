from django.test import TestCase
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.attendance.services.punch_ui import get_punch_ui_state
from apps.core.models import Plant, Tenant
from apps.employees.models import Employee


class PunchUiStateTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="ui", name="UI Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant")
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="P1-001",
            full_name="Tester",
        )

    def test_buttons_always_enabled(self):
        for record in (None, self._record()):
            state = get_punch_ui_state(record)
            self.assertTrue(state["can_clock_in"])
            self.assertTrue(state["can_clock_out"])

    def test_status_pending_without_record(self):
        self.assertEqual(get_punch_ui_state(None)["status"], "pending")

    def test_status_out_when_checked_out(self):
        record = self._record(check_out=timezone.now())
        self.assertEqual(get_punch_ui_state(record)["status"], "out")

    def _record(self, **kwargs):
        defaults = {
            "tenant": self.tenant,
            "plant": self.plant,
            "employee": self.employee,
            "work_date": timezone.localdate(),
            "check_in": timezone.now(),
        }
        defaults.update(kwargs)
        return AttendanceRecord.objects.create(**defaults)
