from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.core.models import Plant, Tenant, User


@override_settings(ALLOWED_HOSTS=["testserver"])
class DashboardContentTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.tenant = Tenant.objects.create(slug="dash", name="Dash Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.user = User.objects.create_user(
            username="dashadmin",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.ADMIN,
        )

    def test_dashboard_shows_informative_sections(self):
        self.client.login(username="dashadmin", password="TestPassword123!")
        response = self.client.get(reverse("web:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Absensi 7 Hari Terakhir")
        self.assertContains(response, "Notifikasi Terbaru")
        self.assertContains(response, "Perlu Persetujuan")
        self.assertContains(response, "Ringkasan Hari Ini")
        self.assertContains(response, "Hadir Hari Ini")
