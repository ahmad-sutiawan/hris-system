from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.core.models import Plant, Tenant, User
from apps.organization.models import Department


@override_settings(ALLOWED_HOSTS=["testserver"])
class AdminManageTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="adm", name="Admin Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.admin = User.objects.create_user(
            username="admin-manage",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.ADMIN,
        )
        self.hr = User.objects.create_user(
            username="hr-manage",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.HR,
        )
        self.client = Client()

    def test_admin_can_access_manage_hub(self):
        self.client.login(username="admin-manage", password="TestPassword123!")
        response = self.client.get(reverse("web:manage_hub"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Console")

    def test_superuser_can_access_manage_hub(self):
        superuser = User.objects.create_superuser(
            username="super-manage",
            password="TestPassword123!",
            email="super@test.local",
        )
        superuser.tenant = self.tenant
        superuser.plant = self.plant
        superuser.save(update_fields=["tenant", "plant"])
        self.client.login(username="super-manage", password="TestPassword123!")
        response = self.client.get(reverse("web:manage_hub"))
        self.assertEqual(response.status_code, 200)

    def test_admin_sidebar_lists_all_apps(self):
        self.client.login(username="admin-manage", password="TestPassword123!")
        response = self.client.get(reverse("web:dashboard"))
        self.assertContains(response, "Administration")
        self.assertContains(response, "Master Data")
        self.assertContains(response, "Department")
        self.assertContains(response, "Komponen Gaji")
        self.assertContains(response, "Penjadwalan Shift")
        self.assertContains(response, "Pengajuan Cuti")
        self.assertNotContains(response, "Struktur Organisasi")
        self.assertContains(response, "Audit Logs")
        self.assertNotContains(response, "/manage/employees/")

    def test_hr_cannot_access_manage_hub(self):
        self.client.login(username="hr-manage", password="TestPassword123!")
        response = self.client.get(reverse("web:manage_hub"))
        self.assertEqual(response.status_code, 302)

    def test_department_crud(self):
        self.client.login(username="admin-manage", password="TestPassword123!")
        create_url = reverse("web:master_create", args=["departments"])
        response = self.client.post(
            create_url,
            {
                "plant": self.plant.pk,
                "code": "HR",
                "name": "Human Resources",
                "is_active": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        dept = Department.objects.get(code="HR", tenant=self.tenant)
        self.assertEqual(dept.name, "Human Resources")

        edit_url = reverse("web:master_edit", args=["departments", dept.pk])
        response = self.client.post(
            edit_url,
            {
                "plant": self.plant.pk,
                "code": "HR",
                "name": "HR Dept",
                "is_active": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        dept.refresh_from_db()
        self.assertEqual(dept.name, "HR Dept")

        delete_url = reverse("web:master_delete", args=["departments", dept.pk])
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Department.objects.filter(pk=dept.pk).exists())

    def test_tenant_manage_module_removed(self):
        self.client.login(username="admin-manage", password="TestPassword123!")
        hub = self.client.get(reverse("web:manage_hub"))
        self.assertEqual(hub.status_code, 200)
        self.assertNotContains(hub, reverse("web:manage_list", args=["tenants"]))
        response = self.client.get(reverse("web:manage_list", args=["tenants"]))
        self.assertEqual(response.status_code, 404)

    def test_manage_list_search(self):
        Department.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="PROD",
            name="Production",
        )
        self.client.login(username="admin-manage", password="TestPassword123!")
        url = reverse("web:master_list", args=["departments"])
        response = self.client.get(url, {"q": "Production"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Production")
