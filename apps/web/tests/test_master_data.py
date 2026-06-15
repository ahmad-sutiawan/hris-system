from decimal import Decimal

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.core.models import Plant, Tenant, User
from apps.leave.models import LeaveType
from apps.organization.models import Department


@override_settings(ALLOWED_HOSTS=["testserver"])
class MasterDataTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="master", name="Master Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.admin = User.objects.create_user(
            username="admin-master",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.ADMIN,
        )
        self.hr = User.objects.create_user(
            username="hr-master",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.HR,
        )
        self.client = Client()

    def test_hr_can_access_master_hub(self):
        self.client.login(username="hr-master", password="TestPassword123!")
        response = self.client.get(reverse("web:master_hub"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Master Data")
        self.assertContains(response, "Department")

    def test_master_sidebar_flat_submenu(self):
        self.client.login(username="hr-master", password="TestPassword123!")
        response = self.client.get(reverse("web:dashboard"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertEqual(content.count("Master Data"), 1)
        self.assertIn("Department", content)
        self.assertIn("Master Shift", content)
        self.assertIn("Komponen Gaji", content)
        self.assertIn("Penjadwalan Shift", content)
        self.assertIn("Pengajuan Cuti", content)
        self.assertIn("Rekap Absensi", content)
        self.assertNotIn("Struktur Organisasi", content)

    def test_hr_cannot_access_manage_hub(self):
        self.client.login(username="hr-master", password="TestPassword123!")
        response = self.client.get(reverse("web:manage_hub"))
        self.assertEqual(response.status_code, 302)

    def test_master_shift_does_not_highlight_operational_shift(self):
        self.client.login(username="hr-master", password="TestPassword123!")
        response = self.client.get(reverse("web:master_list", args=["shifts"]))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertEqual(content.count("hris-nav-link is-active"), 1)

    def test_operational_shift_does_not_highlight_master_shift(self):
        self.client.login(username="hr-master", password="TestPassword123!")
        response = self.client.get(reverse("web:shift_assignment_list"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertEqual(content.count("hris-nav-link is-active"), 1)

    def test_hr_department_crud_via_master(self):
        self.client.login(username="hr-master", password="TestPassword123!")
        create_url = reverse("web:master_create", args=["departments"])
        response = self.client.post(
            create_url,
            {
                "plant": self.plant.pk,
                "name": "Quality Assurance",
                "is_active": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        dept = Department.objects.get(name="Quality Assurance", tenant=self.tenant)
        self.assertTrue(dept.code)
        self.assertEqual(dept.name, "Quality Assurance")

        edit_url = reverse("web:master_edit", args=["departments", dept.pk])
        response = self.client.post(
            edit_url,
            {
                "plant": self.plant.pk,
                "name": "QA Dept",
                "is_active": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        dept.refresh_from_db()
        self.assertEqual(dept.name, "QA Dept")

    def test_leave_type_master_list_search(self):
        LeaveType.objects.create(
            tenant=self.tenant,
            code="CT",
            name="Cuti Tahunan",
            default_quota_days=12,
        )
        self.client.login(username="admin-master", password="TestPassword123!")
        url = reverse("web:master_list", args=["leave-types"])
        response = self.client.get(url, {"q": "Cuti"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cuti Tahunan")

    def test_overtime_type_master_crud(self):
        self.client.login(username="hr-master", password="TestPassword123!")
        create_url = reverse("web:master_create", args=["overtime-types"])
        response = self.client.post(
            create_url,
            {
                "code": "OT-HK-1",
                "name": "Lembur Hari Kerja Jam I",
                "day_category": "workday",
                "hour_from": 1,
                "hour_to": 1,
                "multiplier": "1.5",
                "is_active": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        from apps.attendance.models import OvertimeType

        ot_type = OvertimeType.objects.get(code="OT-HK-1", tenant=self.tenant)
        self.assertEqual(ot_type.multiplier, Decimal("1.5"))

        list_url = reverse("web:master_list", args=["overtime-types"])
        response = self.client.get(list_url, {"q": "Jam I"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lembur Hari Kerja Jam I")

    def test_non_hr_cannot_access_master_data(self):
        employee = User.objects.create_user(
            username="emp-master",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.EMPLOYEE,
        )
        self.client.login(username="emp-master", password="TestPassword123!")
        response = self.client.get(reverse("web:master_hub"))
        self.assertEqual(response.status_code, 302)

    def test_master_slug_not_in_manage_console(self):
        self.client.login(username="admin-master", password="TestPassword123!")
        response = self.client.get(reverse("web:manage_list", args=["departments"]))
        self.assertEqual(response.status_code, 404)
