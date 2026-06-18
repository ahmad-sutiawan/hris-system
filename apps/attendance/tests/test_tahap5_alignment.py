"""Tahap 5 — geo-fence mobile punch & multi-location."""

from datetime import date
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.attendance.models import AttendanceRecord
from apps.attendance.services.geo import GeoFenceError, validate_punch_location
from apps.attendance.services.punch import PunchError, clock_in
from apps.core.models import Plant, PunchLocation, Tenant
from apps.employees.models import Employee


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
