import base64

from django.core.files.base import ContentFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.attendance.services.photo import PhotoError, decode_selfie
from apps.attendance.services.punch import clock_in, clock_out
from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee


def _sample_photo_data_url():
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (400, 400), color=(200, 180, 160)).save(buf, format="JPEG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


class PhotoDecodeTests(TestCase):
    def test_decode_valid_jpeg(self):
        photo = decode_selfie(_sample_photo_data_url())
        self.assertIsInstance(photo, ContentFile)
        self.assertTrue(photo.name.endswith(".jpg"))

    def test_reject_missing_photo(self):
        with self.assertRaises(PhotoError):
            decode_selfie("")

    def test_reject_too_small(self):
        encoded = base64.b64encode(b"tiny").decode("ascii")
        with self.assertRaises(PhotoError):
            decode_selfie(f"data:image/jpeg;base64,{encoded}")


class PunchPhotoTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="punch", name="Punch Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant")
        self.user = User.objects.create_user(
            username="puncher",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.EMPLOYEE,
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="P1-001",
            full_name="Punch Tester",
            user=self.user,
        )
        self.photo = decode_selfie(_sample_photo_data_url())
        self.client = Client()

    def test_clock_in_saves_photo(self):
        record = clock_in(self.employee, photo=self.photo)
        record.refresh_from_db()
        self.assertTrue(record.check_in_photo.name)
        self.assertTrue(record.check_in_photo.storage.exists(record.check_in_photo.name))

    def test_clock_out_saves_photo(self):
        clock_in(self.employee, photo=self.photo)
        out_photo = decode_selfie(_sample_photo_data_url())
        record = clock_out(self.employee, photo=out_photo)
        record.refresh_from_db()
        self.assertTrue(record.check_out_photo.name)

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_web_punch_requires_photo(self):
        self.client.login(username="puncher", password="TestPassword123!")
        response = self.client.post(reverse("web:punch"), {"action": "in"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            AttendanceRecord.objects.filter(employee=self.employee).exists()
        )

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_web_punch_with_photo(self):
        self.client.login(username="puncher", password="TestPassword123!")
        response = self.client.post(
            reverse("web:punch"),
            {"action": "in", "photo": _sample_photo_data_url()},
        )
        self.assertEqual(response.status_code, 302)
        record = AttendanceRecord.objects.get(employee=self.employee)
        self.assertIsNotNone(record.check_in)
        self.assertTrue(record.check_in_photo.name)
