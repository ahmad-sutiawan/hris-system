"""Tests for punch spike scalability (async recalc, cache, throttle)."""

import base64
from io import BytesIO
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.attendance.models import AttendanceRecord, DailyTimesheet
from apps.attendance.services.geo import invalidate_geo_cache
from apps.attendance.services.photo import decode_selfie
from apps.attendance.services.punch import clock_in
from apps.attendance.services.punch_recalc import schedule_daily_timesheet_recalc
from apps.attendance.throttles import PunchRateThrottle
from apps.core.models import Plant, PunchLocation, Tenant, User
from apps.employees.models import Employee


def _sample_photo_data_url():
    buf = BytesIO()
    Image.new("RGB", (400, 400), color=(200, 180, 160)).save(buf, format="JPEG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


class PunchScaleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.tenant = Tenant.objects.create(slug="scale", name="Scale Co")
        self.plant = Plant.objects.create(
            tenant=self.tenant,
            code="S1",
            name="Scale Plant",
            latitude=-6.200000,
            longitude=106.816666,
            geo_fence_radius_m=500,
        )
        self.user = User.objects.create_user(
            username="scaler",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.EMPLOYEE,
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="S1-001",
            full_name="Scale Tester",
            user=self.user,
        )
        self.photo = decode_selfie(_sample_photo_data_url())
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @override_settings(HRIS_PUNCH_ASYNC_RECALC=False)
    def test_punch_sync_recalc_creates_timesheet(self):
        record = clock_in(
            self.employee,
            photo=self.photo,
            source=AttendanceRecord.Source.MOBILE,
            latitude=-6.200100,
            longitude=106.816700,
        )
        self.assertIsNotNone(record.check_in)
        ts = DailyTimesheet.objects.filter(
            employee=self.employee,
            work_date=record.work_date,
        ).first()
        self.assertIsNotNone(ts)
        self.assertIsNotNone(ts.calculated_at)

    @override_settings(HRIS_PUNCH_ASYNC_RECALC=True)
    @mock.patch("apps.attendance.services.punch_recalc.transaction.on_commit")
    def test_async_recalc_scheduled_on_commit(self, on_commit_mock):
        on_commit_mock.side_effect = lambda fn: fn()

        with mock.patch("django_rq.get_queue") as get_queue_mock:
            queue_mock = mock.Mock()
            get_queue_mock.return_value = queue_mock
            record = clock_in(self.employee, photo=self.photo)
            self.assertIsNotNone(record.check_in)
            queue_mock.enqueue.assert_called_once()
            args = queue_mock.enqueue.call_args
            self.assertEqual(args[0][0], "apps.attendance.tasks.recalculate_timesheet_job")
            self.assertEqual(args[0][1], self.employee.pk)

    def test_geo_points_cached(self):
        PunchLocation.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            name="Gate B",
            latitude=-6.201000,
            longitude=106.817000,
            radius_m=200,
        )
        from apps.attendance.services.geo import _points_for_employee

        with self.assertNumQueries(1):
            points = _points_for_employee(self.employee)
        self.assertEqual(len(points), 2)

        with self.assertNumQueries(0):
            cached = _points_for_employee(self.employee)
        self.assertEqual(len(cached), 2)

        invalidate_geo_cache(tenant_id=self.tenant.pk, plant_id=self.plant.pk)

    @mock.patch.object(PunchRateThrottle, "get_rate", return_value="2/minute")
    def test_punch_throttle_is_per_user(self, _rate_mock):
        payload = {
            "photo": _sample_photo_data_url(),
            "latitude": -6.200100,
            "longitude": 106.816700,
        }
        url = "/api/v1/attendance/clock_in/"
        for _ in range(2):
            response = self.client.post(url, payload, format="json")
            self.assertIn(response.status_code, (200, 400))
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 429)

    @override_settings(HRIS_PUNCH_ASYNC_RECALC=False)
    def test_schedule_sync_fallback_when_async_disabled(self):
        work_date = timezone.localdate()
        schedule_daily_timesheet_recalc(self.employee.pk, work_date)
        self.assertTrue(
            DailyTimesheet.objects.filter(
                employee=self.employee,
                work_date=work_date,
            ).exists()
        )
