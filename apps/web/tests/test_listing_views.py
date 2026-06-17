from datetime import date

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.organization.models import Department, JobLevel, JobPosition
from apps.leave.models import LeaveRequest, LeaveType


@override_settings(ALLOWED_HOSTS=["testserver"])
class ListFilteringPaginationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.tenant = Tenant.objects.create(slug="listing", name="Listing Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.admin = User.objects.create_user(
            username="listingadmin",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.ADMIN,
        )
        self.leave_type = LeaveType.objects.create(
            tenant=self.tenant,
            code="CT",
            name="Cuti Tahunan",
        )
        self.department = Department.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="PROD",
            name="Production",
        )
        self.job_level = JobLevel.objects.create(
            tenant=self.tenant,
            code="OPR",
            name="Operator",
            rank=2,
        )
        self.role = JobPosition.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.department,
            code="OPR",
            title="Operator",
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="E001",
            full_name="Budi Santoso",
            department=self.department,
            job_position=self.role,
            job_level=self.job_level,
            join_date=date(2024, 1, 1),
        )
        self.other_department = Department.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="QC",
            name="Quality Control",
        )
        self.other_job_level = JobLevel.objects.create(
            tenant=self.tenant,
            code="LDR",
            name="Leader",
            rank=6,
        )
        self.other_role = JobPosition.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.other_department,
            code="QC1",
            title="QC Inspector",
        )
        self.other_employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="E002",
            full_name="Siti Aminah",
            department=self.other_department,
            job_position=self.other_role,
            job_level=self.other_job_level,
            join_date=date(2024, 1, 1),
        )
        for i in range(30):
            LeaveRequest.objects.create(
                tenant=self.tenant,
                employee=self.employee,
                leave_type=self.leave_type,
                start_date=date(2024, 2, 1),
                end_date=date(2024, 2, 2),
                reason=f"Request {i}",
            )

    def test_leave_list_pagination(self):
        self.client.login(username="listingadmin", password="TestPassword123!")
        response = self.client.get(reverse("web:leave_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Halaman 1 /")
        self.assertContains(response, "Export CSV")

    def test_leave_export_respects_search(self):
        self.client.login(username="listingadmin", password="TestPassword123!")
        response = self.client.get(reverse("web:leave_list"), {"export": "csv", "q": "Budi"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        body = response.content.decode()
        self.assertIn("Budi Santoso", body)

    def test_employee_list_date_filter(self):
        self.client.login(username="listingadmin", password="TestPassword123!")
        response = self.client.get(
            reverse("web:employee_list"),
            {"date_from": "2025-01-01"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Belum ada data karyawan")

    def test_employee_list_renders_filter_dropdown_options(self):
        self.client.login(username="listingadmin", password="TestPassword123!")
        response = self.client.get(reverse("web:employee_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="job_position"')
        self.assertContains(response, 'name="department"')
        self.assertContains(response, 'name="job_level"')
        self.assertContains(response, "Organization")
        self.assertContains(response, "Job Position")
        self.assertContains(response, f'value="{self.role.pk}"')
        self.assertContains(response, "Operator")
        self.assertContains(response, f'value="{self.department.pk}"')
        self.assertContains(response, "Production")
        self.assertContains(response, f'value="{self.job_level.pk}"')
        self.assertNotContains(response, "QuerySet")

    def test_employee_list_filters_by_role_department_and_level(self):
        self.client.login(username="listingadmin", password="TestPassword123!")
        response = self.client.get(
            reverse("web:employee_list"),
            {
                "job_position": str(self.other_role.pk),
                "department": str(self.other_department.pk),
                "job_level": str(self.other_job_level.pk),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Siti Aminah")
        self.assertNotContains(response, "Budi Santoso")
