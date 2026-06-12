from datetime import timedelta
from decimal import Decimal

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

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

    def test_employee_sees_announcement_banner_on_dashboard(self):
        self.client.login(username="emp-ann", password="TestPassword123!")
        response = self.client.get(reverse("web:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Libur Nasional")
        self.assertContains(response, "hris-announcement-stack")

    def test_announcement_list_and_detail(self):
        self.client.login(username="emp-ann", password="TestPassword123!")
        response = self.client.get(reverse("web:announcement_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Libur Nasional")

        detail = self.client.get(reverse("web:announcement_detail", args=[self.announcement.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Konten Lengkap")
        self.assertContains(detail, "Seluruh karyawan libur")

        self.announcement.refresh_from_db()
        self.assertEqual(self.announcement.view_count, 1)

    def test_dismiss_hides_banner(self):
        self.client.login(username="emp-ann", password="TestPassword123!")
        self.client.post(reverse("web:announcement_dismiss", args=[self.announcement.pk]))
        response = self.client.get(reverse("web:dashboard"))
        self.assertNotContains(response, "hris-announcement-stack")

    def test_admin_can_manage_announcements(self):
        self.client.login(username="admin-ann", password="TestPassword123!")
        response = self.client.get(reverse("web:manage_list", args=["announcements"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Libur Nasional")

    def test_plant_targeting_excludes_other_plant(self):
        plant2 = Plant.objects.create(tenant=self.tenant, code="P2", name="Plant 2")
        self.announcement.plant = plant2
        self.announcement.save(update_fields=["plant"])

        self.client.login(username="emp-ann", password="TestPassword123!")
        response = self.client.get(reverse("web:announcement_list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Libur Nasional")
