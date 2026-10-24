from datetime import date

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.core.models import Plant, Tenant, User
from apps.core.xlsx_io import XLSX_CONTENT_TYPE, read_xlsx_rows
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
        self.assertContains(response, "Export Excel")

    def test_leave_export_respects_search(self):
        self.client.login(username="listingadmin", password="TestPassword123!")
        response = self.client.get(reverse("web:leave_list"), {"export": "csv", "q": "Budi"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], XLSX_CONTENT_TYPE)
        headers, rows = read_xlsx_rows(response.content)
        self.assertTrue(rows)
        self.assertIn("Budi Santoso", str(rows[0].values()))

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

    def test_employee_export_uses_directory_columns_and_branch_filter(self):
        other_plant = Plant.objects.create(
            tenant=self.tenant,
            code="P2",
            name="Plant 2",
        )
        Employee.objects.create(
            tenant=self.tenant,
            plant=other_plant,
            employee_id="E003",
            full_name="Dewi Lestari",
            mother_name="Ibu Dewi",
            status_employee="Harian",
            join_date=date(2024, 3, 1),
        )
        self.client.login(username="listingadmin", password="TestPassword123!")
        page = self.client.get(reverse("web:employee_list"), {"plant": str(other_plant.pk)})
        self.assertContains(page, "Dewi Lestari")
        self.assertNotContains(page, "Budi Santoso")
        self.assertContains(page, "Semua Branch")
        self.assertContains(page, "Join Date")

        exported = self.client.get(
            reverse("web:employee_list"),
            {"export": "xlsx", "plant": str(other_plant.pk), "q": "Dewi"},
        )
        self.assertEqual(exported.status_code, 200)
        headers, rows = read_xlsx_rows(exported.content)
        self.assertEqual(headers[0], "Employee ID")
        self.assertEqual(headers[1], "Full Name")
        self.assertIn("NIK (NPWP 16 Digit)", headers)
        self.assertIn("Nama Ibu Kandung", headers)
        self.assertIn("Shift Default", headers)
        self.assertNotIn("Base Salary", headers)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Full Name"], "Dewi Lestari")
        self.assertEqual(rows[0]["Nama Ibu Kandung"], "Ibu Dewi")
        self.assertEqual(rows[0]["Branch Name"], "Plant 2")
