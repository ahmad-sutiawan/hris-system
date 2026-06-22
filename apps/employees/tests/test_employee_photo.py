from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase

from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.employees.serializers import EmployeeDirectorySerializer, EmployeeSelfSerializer
from apps.employees.services.photo import employee_photo_url


class EmployeePhotoSerializerTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Photo Tenant", code="photo-tenant")
        self.plant = Plant.objects.create(tenant=self.tenant, code="BPS", name="BPS")
        self.user = User.objects.create_user(
            username="photo-user",
            password="secret123",
            tenant=self.tenant,
            role=User.Role.EMPLOYEE,
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="9001",
            full_name="Photo Tester",
            email="photo@example.com",
            phone="081234567890",
            join_date="2024-01-01",
            photo=SimpleUploadedFile(
                "profile.png",
                (
                    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
                    b"\x00\x00\x00\x00IEND\xaeB`\x82"
                ),
                content_type="image/png",
            ),
        )
        self.request = RequestFactory().get("/")

    def test_employee_directory_includes_photo_url(self):
        data = EmployeeDirectorySerializer(
            self.employee,
            context={"request": self.request},
        ).data
        self.assertIn("photo_url", data)
        self.assertTrue(data["photo_url"])

    def test_employee_self_includes_photo_url(self):
        data = EmployeeSelfSerializer(
            self.employee,
            context={"request": self.request},
        ).data
        self.assertEqual(data["photo_url"], employee_photo_url(self.employee, request=self.request))

    def test_employee_without_photo_returns_null_url(self):
        self.employee.photo = ""
        self.employee.save(update_fields=["photo"])
        data = EmployeeDirectorySerializer(self.employee).data
        self.assertIsNone(data["photo_url"])
