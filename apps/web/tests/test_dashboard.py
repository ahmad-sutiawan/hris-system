from decimal import Decimal

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.leave.models import LeaveRequest, LeaveType
from apps.organization.models import Department, JobPosition


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

    def test_dashboard_profile_summary_uses_job_position_title(self):
        dept = Department.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="HR",
            name="Human Resources",
        )
        job = JobPosition.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=dept,
            code="OPR",
            title="Operator Produksi",
        )
        employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=dept,
            job_position=job,
            user=self.user,
            employee_id="E100",
            full_name="Ayub Test",
        )
        self.user.employee_profile = employee
        self.client.login(username="dashadmin", password="TestPassword123!")
        response = self.client.get(reverse("web:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Operator Produksi")
        self.assertContains(response, "Profil Saya")

    def test_dashboard_shows_on_leave_today_avatars(self):
        dept = Department.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="HR",
            name="Human Resources",
        )
        job = JobPosition.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=dept,
            code="OPR",
            title="Operator Produksi",
        )
        leave_type = LeaveType.objects.create(
            tenant=self.tenant,
            code="CT",
            name="Cuti Tahunan",
            default_quota_days=12,
        )
        employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=dept,
            job_position=job,
            employee_id="E200",
            full_name="Siti Cuti",
            base_salary=Decimal("5000000"),
            status=Employee.Status.PERMANENT,
        )
        today = timezone.localdate()
        LeaveRequest.objects.create(
            tenant=self.tenant,
            employee=employee,
            leave_type=leave_type,
            start_date=today,
            end_date=today,
            days=Decimal("1"),
            status=LeaveRequest.Status.APPROVED,
        )

        self.client.login(username="dashadmin", password="TestPassword123!")
        response = self.client.get(reverse("web:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sedang Cuti Hari Ini")
        self.assertContains(response, "Siti Cuti")
        self.assertContains(response, "hris-leave-today-avatar")
        self.assertContains(response, "Cuti Tahunan")
