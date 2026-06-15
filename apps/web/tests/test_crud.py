from datetime import timedelta
from decimal import Decimal

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.leave.models import LeaveBalance, LeaveRequest, LeaveType
from apps.organization.models import Department, JobPosition, LegalEntity
from apps.payroll.models import PayrollRun
from apps.shifts.models import Shift, ShiftAssignment


@override_settings(ALLOWED_HOSTS=["testserver"])
class WebCRUDTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.tenant = Tenant.objects.create(slug="crud", name="CRUD Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.dept = Department.objects.create(
            tenant=self.tenant, plant=self.plant, code="HR", name="HR"
        )
        self.job = JobPosition.objects.create(
            tenant=self.tenant, plant=self.plant, code="OP", title="Operator", department=self.dept
        )
        self.admin = User.objects.create_user(
            username="admincrud",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.ADMIN,
        )
        self.employee_user = User.objects.create_user(
            username="empcrud",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.EMPLOYEE,
            email="emp@crud.local",
        )
        self.manager = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            job_position=self.job,
            employee_id="P1-MGR",
            full_name="Manager",
            base_salary=Decimal("7000000"),
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            job_position=self.job,
            manager=self.manager,
            employee_id="P1-001",
            full_name="Budi CRUD",
            user=self.employee_user,
            base_salary=Decimal("5000000"),
            status=Employee.Status.PERMANENT,
        )
        self.leave_type = LeaveType.objects.create(
            tenant=self.tenant,
            code="CT",
            name="Cuti Tahunan",
            default_quota_days=12,
        )
        self.shift = Shift.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            name="Pagi",
            code="PAGI",
            scheduled_check_in="07:00",
            scheduled_check_out="15:00",
        )
        self.client.login(username="admincrud", password="TestPassword123!")
        self.today = timezone.localdate()

    def test_form_pages_render(self):
        pages = [
            reverse("web:employee_create"),
            reverse("web:shift_assign"),
            reverse("web:payroll_create"),
            reverse("web:leave_create"),
            reverse("web:overtime_create"),
        ]
        for url in pages:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, msg=url)

    def test_employee_create_and_edit(self):
        data = {
            "employee_id": "P1-NEW",
            "full_name": "Baru",
            "nik": "111",
            "email": "baru@test.com",
            "phone": "",
            "plant": self.plant.pk,
            "department": self.dept.pk,
            "job_position": self.job.pk,
            "manager": self.manager.pk,
            "join_date": self.today.isoformat(),
            "status": "permanent",
            "salary_scheme": "monthly",
            "base_salary": "4500000",
            "allowance_transport": "0",
            "allowance_meal": "0",
            "allowance_position": "0",
            "tax_status": "TK/0",
            "npwp": "",
            "bpjs_kesehatan_number": "",
            "bpjs_ketenagakerjaan_number": "",
            "bank_name": "",
            "bank_account_number": "",
            "bank_account_name": "",
        }
        response = self.client.post(reverse("web:employee_create"), data)
        self.assertEqual(response.status_code, 302)
        emp = Employee.objects.get(employee_id="P1-NEW")
        balance = LeaveBalance.objects.get(employee=emp, leave_type=self.leave_type)
        self.assertEqual(balance.remaining, Decimal("12"))
        data["full_name"] = "Baru Updated"
        response = self.client.post(reverse("web:employee_edit", args=[emp.pk]), data)
        self.assertEqual(response.status_code, 302)
        emp.refresh_from_db()
        self.assertEqual(emp.full_name, "Baru Updated")

    def test_employee_edit_preserves_legal_entity(self):
        legal = LegalEntity.objects.create(
            tenant=self.tenant,
            name="PT Demo Legal",
            npwp="01.234.567.8-901.000",
        )
        self.employee.legal_entity = legal
        self.employee.save(update_fields=["legal_entity", "updated_at"])

        data = {
            "employee_id": self.employee.employee_id,
            "full_name": "Budi CRUD Updated",
            "nik": "",
            "email": "emp@crud.local",
            "phone": "",
            "plant": self.plant.pk,
            "department": self.dept.pk,
            "job_position": self.job.pk,
            "manager": self.manager.pk,
            "join_date": "",
            "status": "permanent",
            "salary_scheme": "monthly",
            "base_salary": "5000000",
            "allowance_transport": "0",
            "allowance_meal": "0",
            "allowance_position": "0",
            "tax_status": "",
            "npwp": "",
            "bpjs_kesehatan_number": "",
            "bpjs_ketenagakerjaan_number": "",
            "bank_name": "",
            "bank_account_number": "",
            "bank_account_name": "",
        }
        response = self.client.post(reverse("web:employee_edit", args=[self.employee.pk]), data)
        self.assertEqual(response.status_code, 302)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.full_name, "Budi CRUD Updated")
        self.assertEqual(self.employee.legal_entity_id, legal.pk)

    def test_employee_edit_assigns_default_shift(self):
        evening = Shift.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            name="Sore",
            code="SORE",
            scheduled_check_in="15:00",
            scheduled_check_out="23:00",
        )
        data = {
            "employee_id": self.employee.employee_id,
            "full_name": self.employee.full_name,
            "nik": "",
            "email": "emp@crud.local",
            "phone": "",
            "plant": self.plant.pk,
            "department": self.dept.pk,
            "job_position": self.job.pk,
            "manager": self.manager.pk,
            "default_shift": evening.pk,
            "join_date": "",
            "status": "permanent",
            "salary_scheme": "monthly",
            "base_salary": "5000000",
            "allowance_transport": "0",
            "allowance_meal": "0",
            "allowance_position": "0",
            "tax_status": "",
            "npwp": "",
            "bpjs_kesehatan_number": "",
            "bpjs_ketenagakerjaan_number": "",
            "bank_name": "",
            "bank_account_number": "",
            "bank_account_name": "",
        }
        response = self.client.post(reverse("web:employee_edit", args=[self.employee.pk]), data)
        self.assertEqual(response.status_code, 302)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.default_shift_id, evening.pk)
        assignment = ShiftAssignment.objects.get(employee=self.employee, work_date=self.today)
        self.assertEqual(assignment.shift_id, evening.pk)

    def test_shift_assign_update_or_create(self):
        data = {
            "employee": self.employee.pk,
            "shift": self.shift.pk,
            "work_date": self.today.isoformat(),
        }
        response = self.client.post(reverse("web:shift_assign"), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ShiftAssignment.objects.filter(employee=self.employee).count(), 1)
        response = self.client.post(reverse("web:shift_assign"), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ShiftAssignment.objects.filter(employee=self.employee).count(), 1)

    def test_payroll_create_and_edit(self):
        data = {
            "plant": self.plant.pk,
            "period_start": self.today.replace(day=1).isoformat(),
            "period_end": self.today.isoformat(),
            "notes": "test",
        }
        response = self.client.post(reverse("web:payroll_create"), data)
        self.assertEqual(response.status_code, 302)
        run = PayrollRun.objects.get(tenant=self.tenant)
        data["notes"] = "updated"
        response = self.client.post(reverse("web:payroll_edit", args=[run.pk]), data)
        self.assertEqual(response.status_code, 302)
        run.refresh_from_db()
        self.assertEqual(run.notes, "updated")

    def test_leave_create_as_hr_for_employee(self):
        start = self.today + timedelta(days=10)
        data = {
            "employee": self.employee.pk,
            "leave_type": self.leave_type.pk,
            "start_date": start.isoformat(),
            "end_date": start.isoformat(),
            "reason": "Libur",
        }
        response = self.client.post(reverse("web:leave_create"), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(LeaveRequest.objects.filter(employee=self.employee).exists())

    def test_leave_form_date_widget_is_html5(self):
        from apps.web.forms import LeaveRequestForm

        form = LeaveRequestForm(tenant=self.tenant, show_employee_picker=False, profile=self.employee)
        html = form.as_table()
        self.assertIn('type="date"', html)
        self.assertIn("hris-date-input", html)
        self.assertEqual(form.fields["start_date"].input_formats, ["%Y-%m-%d"])

    def test_leave_create_as_employee_with_iso_dates(self):
        emp_user = User.objects.create_user(
            username="budi-crud",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.EMPLOYEE,
        )
        self.employee.user = emp_user
        self.employee.save(update_fields=["user"])
        self.client.logout()
        self.client.login(username="budi-crud", password="TestPassword123!")
        start = self.today + timedelta(days=14)
        data = {
            "leave_type": self.leave_type.pk,
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=1)).isoformat(),
            "reason": "Cuti",
        }
        response = self.client.post(reverse("web:leave_create"), data)
        self.assertEqual(response.status_code, 302, msg=response.content.decode()[:500])

    def test_employee_deactivate(self):
        response = self.client.post(reverse("web:employee_deactivate", args=[self.employee.pk]))
        self.assertEqual(response.status_code, 302)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.status, Employee.Status.INACTIVE)
