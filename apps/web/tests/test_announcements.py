from datetime import timedelta
from decimal import Decimal

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import Announcement, Plant, Tenant, User
from apps.employees.models import Employee
from apps.organization.models import Department, JobPosition


@override_settings(ALLOWED_HOSTS=["testserver"])
class AnnouncementFeatureTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.tenant = Tenant.objects.create(slug="ann", name="Announcement Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.dept = Department.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="HR",
            name="HR",
        )
        self.job = JobPosition.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="OP",
            title="Operator",
            department=self.dept,
        )
        self.admin = User.objects.create_user(
            username="admin-ann",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.ADMIN,
        )
        self.employee_user = User.objects.create_user(
            username="emp-ann",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.EMPLOYEE,
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            job_position=self.job,
            employee_id="P1-001",
            full_name="Budi Ann",
            user=self.employee_user,
            base_salary=Decimal("5000000"),
            status=Employee.Status.PERMANENT,
        )
        self.employee_user.set_password(self.employee.employee_id)
        self.employee_user.save(update_fields=["password"])
        now = timezone.now()
        self.announcement = Announcement.objects.create(
            tenant=self.tenant,
            title="Libur Nasional",
            summary="Kantor tutup tanggal merah.",
            body="Seluruh karyawan libur pada tanggal yang ditentukan.",
            category=Announcement.Category.GENERAL,
            priority=Announcement.Priority.HIGH,
            publish_start=now - timedelta(hours=1),
            is_active=True,
            is_pinned=True,
            created_by=self.admin,
        )

    def _login_employee(self):
        self.assertTrue(
            self.client.login(
                username=self.employee.employee_id,
                password=self.employee.employee_id,
            )
        )

    def test_employee_sees_announcement_banner_on_dashboard(self):
        self._login_employee()
        response = self.client.get(reverse("web:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Libur Nasional")
        self.assertContains(response, "hris-announcement-stack")

    def test_announcement_list_and_detail(self):
        self._login_employee()
        response = self.client.get(reverse("web:announcement_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Libur Nasional")
        self.assertNotContains(response, "Buat Pengumuman")

        detail = self.client.get(reverse("web:announcement_detail", args=[self.announcement.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Konten Lengkap")
        self.assertContains(detail, "Seluruh karyawan libur")

        self.announcement.refresh_from_db()
        self.assertEqual(self.announcement.view_count, 1)

    def test_dismiss_hides_banner(self):
        self._login_employee()
        self.client.post(reverse("web:announcement_dismiss", args=[self.announcement.pk]))
        response = self.client.get(reverse("web:dashboard"))
        self.assertNotContains(response, "hris-announcement-stack")

    def test_admin_can_manage_announcements(self):
        self.client.login(username="admin-ann", password="TestPassword123!")
        response = self.client.get(reverse("web:announcement_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Buat Pengumuman")
        self.assertContains(response, "Libur Nasional")

    def test_hr_can_publish_announcement_to_web_and_app(self):
        self.client.login(username="admin-ann", password="TestPassword123!")
        manage = self.client.get(reverse("web:announcement_list"))
        self.assertEqual(manage.status_code, 200)
        self.assertContains(manage, "Buat Pengumuman")
        self.assertContains(manage, "Libur Nasional")

        start = timezone.localtime().strftime("%Y-%m-%dT%H:%M")
        created = self.client.post(
            reverse("web:announcement_create"),
            {
                "title": "Rapat Semua Plant",
                "summary": "Hadir tepat waktu.",
                "body": "Seluruh karyawan wajib hadir.",
                "category": Announcement.Category.GENERAL,
                "priority": Announcement.Priority.HIGH,
                "publish_start": start,
                "is_active": "on",
                "tags_input": "rapat, wajib",
            },
        )
        self.assertEqual(created.status_code, 302)
        announcement = Announcement.objects.get(title="Rapat Semua Plant")
        self.assertIsNone(announcement.plant_id)
        self.assertEqual(announcement.target_roles, [])
        self.assertEqual(announcement.tags, ["rapat", "wajib"])
        self.assertEqual(announcement.created_by, self.admin)
        self.assertTrue(announcement.reaches_everyone)

        self._login_employee()
        web = self.client.get(reverse("web:announcement_list"))
        self.assertContains(web, "Rapat Semua Plant")
        detail = self.client.get(reverse("web:announcement_detail", args=[announcement.pk]))
        self.assertContains(detail, "Seluruh karyawan wajib hadir.")

        api = APIClient()
        api.force_authenticate(user=self.employee_user)
        mobile = api.get("/api/v1/announcements/")
        self.assertEqual(mobile.status_code, 200)
        titles = [item["title"] for item in mobile.json()]
        self.assertIn("Rapat Semua Plant", titles)
        dashboard = api.get("/api/v1/mobile/dashboard/")
        featured = [item["title"] for item in dashboard.json()["featured_announcements"]]
        self.assertIn("Rapat Semua Plant", featured)

    def test_employee_cannot_create_announcement(self):
        self._login_employee()
        response = self.client.get(reverse("web:announcement_create"))
        self.assertRedirects(response, reverse("web:dashboard"))
        self.assertEqual(Announcement.objects.count(), 1)

    def test_plant_targeting_excludes_other_plant(self):
        plant2 = Plant.objects.create(tenant=self.tenant, code="P2", name="Plant 2")
        self.announcement.plant = plant2
        self.announcement.save(update_fields=["plant"])

        self._login_employee()
        response = self.client.get(reverse("web:announcement_list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Libur Nasional")
