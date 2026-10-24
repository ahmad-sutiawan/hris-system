"""Tahap 5 — geo-fence mobile punch & multi-location."""

from datetime import date, datetime, time
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.attendance.models import AttendanceRecord
from apps.attendance.services.geo import (
    GeoFenceError,
    punch_locations_for_employee,
    validate_punch_location,
)
from apps.attendance.services.punch import PunchError, clock_in
from apps.core.models import Plant, PunchLocation, Tenant, User
from apps.employees.models import Employee
from apps.shifts.models import Shift, ShiftAssignment


def _photo():
    buf = BytesIO()
    Image.new("RGB", (400, 400), color=(200, 180, 160)).save(buf, format="JPEG")
    return SimpleUploadedFile("selfie.jpg", buf.getvalue(), content_type="image/jpeg")


@override_settings(ALLOWED_HOSTS=["testserver"])
class GeoFenceTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="t5", name="T5 Co")
        self.plant = Plant.objects.create(
            tenant=self.tenant,
            code="P1",
            name="Plant Utama",
            latitude=Decimal("-6.2088000"),
            longitude=Decimal("106.8456000"),
            geo_fence_radius_m=200,
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="E001",
            full_name="Field Worker",
            join_date=date(2024, 1, 1),
        )

    def test_no_coordinates_skips_geo_check(self):
        self.plant.latitude = None
        self.plant.longitude = None
        self.plant.save(update_fields=["latitude", "longitude"])
        validate_punch_location(self.employee, None, None)

    def test_inside_plant_radius_passes(self):
        validate_punch_location(self.employee, -6.2089, 106.8457)

    def test_outside_plant_raises_with_nearest_hint(self):
        with self.assertRaises(GeoFenceError) as ctx:
            validate_punch_location(self.employee, -6.3000, 106.9000)
        self.assertIn("Plant Utama", str(ctx.exception))
        self.assertIn("radius 200", str(ctx.exception))

    def test_missing_gps_when_fence_configured(self):
        with self.assertRaises(GeoFenceError) as ctx:
            validate_punch_location(self.employee, None, None)
        self.assertIn("GPS wajib", str(ctx.exception))

    def test_hybrid_punch_location_accepted(self):
        PunchLocation.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            name="Kantor Cabang",
            latitude=Decimal("-6.1751000"),
            longitude=Decimal("106.8650000"),
            radius_m=150,
        )
        validate_punch_location(self.employee, -6.1752, 106.8651)

    def test_punch_location_on_parent_pt_for_branch_employee(self):
        pt = Plant.objects.create(
            tenant=self.tenant,
            code="PT1",
            name="Plant Induk",
            entity_type=Plant.EntityType.PT,
        )
        branch = Plant.objects.create(
            tenant=self.tenant,
            parent=pt,
            code="BR1",
            name="Cabang A",
            entity_type=Plant.EntityType.BRANCH,
            latitude=Decimal("-6.2088000"),
            longitude=Decimal("106.8456000"),
            geo_fence_radius_m=200,
        )
        self.employee.plant = branch
        self.employee.save(update_fields=["plant"])
        PunchLocation.objects.create(
            tenant=self.tenant,
            plant=pt,
            name="Site PT",
            latitude=Decimal("-6.1751000"),
            longitude=Decimal("106.8650000"),
            radius_m=150,
        )
        validate_punch_location(self.employee, -6.1752, 106.8651)

    def test_map_points_include_parent_plant_radius(self):
        pt = Plant.objects.create(
            tenant=self.tenant,
            code="PTMAP",
            name="Kantor Pusat",
            entity_type=Plant.EntityType.PT,
            latitude=Decimal("-6.1751000"),
            longitude=Decimal("106.8650000"),
            geo_fence_radius_m=180,
        )
        branch = Plant.objects.create(
            tenant=self.tenant,
            parent=pt,
            code="BRMAP",
            name="Information & Technology",
            entity_type=Plant.EntityType.BRANCH,
        )
        self.employee.plant = branch
        self.employee.save(update_fields=["plant"])
        locations = punch_locations_for_employee(self.employee)
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0]["name"], "Kantor Pusat")
        self.assertEqual(locations[0]["radius_m"], 180)

    def test_radius_change_applies_without_stale_cache(self):
        validate_punch_location(self.employee, -6.2097, 106.8456)
        self.plant.geo_fence_radius_m = 50
        self.plant.save(update_fields=["geo_fence_radius_m"])
        with self.assertRaises(GeoFenceError):
            validate_punch_location(self.employee, -6.2097, 106.8456)

    def test_branch_cache_follows_parent_location_edit(self):
        pt = Plant.objects.create(
            tenant=self.tenant,
            code="PT2",
            name="BPS OFFICE",
            entity_type=Plant.EntityType.PT,
        )
        branch = Plant.objects.create(
            tenant=self.tenant,
            parent=pt,
            code="BR2",
            name="Cabang Harian",
            entity_type=Plant.EntityType.BRANCH,
        )
        self.employee.plant = branch
        self.employee.save(update_fields=["plant"])
        location = PunchLocation.objects.create(
            tenant=self.tenant,
            plant=pt,
            name="BPS OFFICE",
            latitude=Decimal("-6.1751000"),
            longitude=Decimal("106.8650000"),
            radius_m=150,
        )
        validate_punch_location(self.employee, -6.1752, 106.8651)
        location.radius_m = 10
        location.save(update_fields=["radius_m"])
        with self.assertRaises(GeoFenceError) as ctx:
            validate_punch_location(self.employee, -6.1752, 106.8651)
        self.assertIn("BPS OFFICE", str(ctx.exception))

    def test_branch_owned_location_is_allowed(self):
        pt = Plant.objects.create(
            tenant=self.tenant,
            code="PT3",
            name="Plant Induk",
            entity_type=Plant.EntityType.PT,
        )
        branch = Plant.objects.create(
            tenant=self.tenant,
            parent=pt,
            code="BR3",
            name="Workshop",
            entity_type=Plant.EntityType.BRANCH,
        )
        self.employee.plant = branch
        self.employee.save(update_fields=["plant"])
        PunchLocation.objects.create(
            tenant=self.tenant,
            plant=branch,
            name="Workshop B",
            latitude=Decimal("-6.3000000"),
            longitude=Decimal("106.9000000"),
            radius_m=80,
        )
        validate_punch_location(self.employee, -6.3001, 106.9000)

    def test_mobile_punch_outside_geo_rejected(self):
        with self.assertRaises(PunchError) as ctx:
            clock_in(
                self.employee,
                source=AttendanceRecord.Source.MOBILE,
                photo=_photo(),
                latitude=-6.3000,
                longitude=106.9000,
            )
        self.assertIn("luar area", str(ctx.exception).lower())

    def test_web_punch_outside_geo_allowed(self):
        record = clock_in(
            self.employee,
            source=AttendanceRecord.Source.WEB,
            photo=_photo(),
            latitude=-6.3000,
            longitude=106.9000,
        )
        self.assertIsNotNone(record.check_in)


@override_settings(ALLOWED_HOSTS=["testserver"])
class ServerTimeApiTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="t5time", name="T5 Time")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant")
        self.user = User.objects.create_user(
            username="punch-emp",
            password="TestPassword123!",
            tenant=self.tenant,
            role=User.Role.EMPLOYEE,
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="E900",
            full_name="Server Clock",
            user=self.user,
            join_date=date(2024, 1, 1),
        )
        shift = Shift.objects.create(
            tenant=self.tenant,
            code="PAGI",
            name="Shift Pagi",
            scheduled_check_in=time(7, 0),
            scheduled_check_out=time(15, 0),
        )
        ShiftAssignment.objects.create(
            tenant=self.tenant,
            employee=self.employee,
            shift=shift,
            work_date=timezone.localdate(),
            scheduled_check_in=time(7, 0),
            scheduled_check_out=time(15, 0),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_server_time_ignores_client_clock_and_returns_shift(self):
        response = self.client.get(
            "/api/v1/attendance/server-time/",
            {"punch": "in", "punched_at": "2000-01-01T00:00:00+07:00"},
        )
        self.assertEqual(response.status_code, 200)
        server_time = datetime.fromisoformat(response.data["server_time"])
        self.assertGreater(server_time.year, 2020)
        self.assertEqual(response.data["matched_shift"]["shift_code"], "PAGI")
        self.assertEqual(response.data["matched_shift"]["shift_name"], "Shift Pagi")
