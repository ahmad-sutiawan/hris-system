import base64
from io import BytesIO

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from apps.attendance.models import AttendanceRecord
from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee


def _sample_jpeg():
    buf = BytesIO()
    Image.new("RGB", (80, 80), color=(120, 90, 60)).save(buf, format="JPEG")
    return ContentFile(buf.getvalue(), name="punch-test.jpg")


@override_settings(HRIS_MEDIA_PROTECTED=True)
class ApiMediaFileTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="media-api", name="Media API Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant")
        self.user = User.objects.create_user(
            username="media-user",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.EMPLOYEE,
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="M-001",
            full_name="Media User",
            user=self.user,
        )
        self.record = AttendanceRecord.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee=self.employee,
            work_date="2026-06-15",
            check_in_photo=_sample_jpeg(),
            source=AttendanceRecord.Source.MOBILE,
        )
        self.client = APIClient()

    def test_authenticated_user_can_fetch_own_punch_photo_via_api(self):
        self.client.force_authenticate(user=self.user)
        path = self.record.check_in_photo.name
        url = reverse("api_media", kwargs={"path": path})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        body = b"".join(response.streaming_content)
        self.assertTrue(body.startswith(b"\xff\xd8"))

    def test_other_user_cannot_fetch_photo(self):
        other = User.objects.create_user(
            username="other-user",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.EMPLOYEE,
        )
        Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="M-002",
            full_name="Other User",
            user=other,
        )
        self.client.force_authenticate(user=other)
        path = self.record.check_in_photo.name
        url = reverse("api_media", kwargs={"path": path})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_anonymous_cannot_fetch_photo(self):
        path = self.record.check_in_photo.name
        url = reverse("api_media", kwargs={"path": path})
        response = self.client.get(url)
        self.assertIn(response.status_code, (401, 403))
