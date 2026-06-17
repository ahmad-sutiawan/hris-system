import base64
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.attendance.models import AttendanceRecord, DailyTimesheet, OvertimeRequest, OvertimeType
from apps.attendance.services.photo import decode_selfie
from apps.attendance.services.punch import clock_in, clock_out
from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.leave.models import LeaveBalance, LeaveRequest, LeaveType
from apps.organization.models import Department, JobPosition
from apps.shifts.models import Shift, ShiftAssignment


def _sample_photo_data_url():
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (400, 400), color=(200, 180, 160)).save(buf, format="JPEG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


@override_settings(ALLOWED_HOSTS=["testserver"])
class NewEmployeeOnboardingE2ETest(TestCase):
    """QA: full new-hire path — register, shift, leave quota, CI/CO, cuti, lembur (OT)."""

    def setUp(self):
        self.tenant = Tenant.objects.create(slug="e2e", name="E2E Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.dept = Department.objects.create(
            tenant=self.tenant, plant=self.plant, code="PROD", name="Produksi"
        )
        self.job = JobPosition.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="OP",
            title="Operator",
            department=self.dept,
        )
        self.leave_type = LeaveType.objects.create(
            tenant=self.tenant,
            code="CT",
            name="Cuti Tahunan",
            default_quota_days=Decimal("12"),
        )
        self.overtime_type = OvertimeType.objects.create(
            tenant=self.tenant,
            code="OT-HK-1",
            name="Lembur Hari Kerja Jam I",
            day_category=OvertimeType.DayCategory.WORKDAY,
            hour_from=1,
            hour_to=1,
            multiplier=Decimal("1.5"),
        )
        self.shift = Shift.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            name="Pagi",
            code="PAGI",
            scheduled_check_in=time(7, 0),
            scheduled_check_out=time(15, 0),
        )
        self.plant.default_shift = self.shift
        self.plant.save(update_fields=["default_shift"])
        self.today = timezone.localdate()
        self.tz = timezone.get_current_timezone()
        self.hr = User.objects.create_user(
            username="hre2e",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.HR,
        )
        self.manager_employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            job_position=self.job,
            employee_id="P1-MGR",
            full_name="Manager E2E",
            email="manager@e2e.local",
            phone="08111111111",
            nik="3201010101010099",
            gender=Employee.Gender.MALE,
            marital_status=Employee.MaritalStatus.SINGLE,
            birth_place="Jakarta",
            join_date=self.today,
        )
        self.new_user = User.objects.create_user(
            username="newhire",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.EMPLOYEE,
            email="newhire@e2e.local",
        )
        self.client = Client()
        self.api = APIClient()

    def _employee_form_data(self, **overrides):
        data = {
            "employee_id": "P1-NEW",
            "full_name": "Karyawan Baru",
            "nik": "3201010101010001",
            "email": "newhire@e2e.local",
            "phone": "08123456789",
            "address": "Jakarta Selatan",
            "mother_name": "Ibu Baru",
            "birth_place": "Jakarta",
            "birth_date": "1995-05-15",
            "gender": Employee.Gender.MALE,
            "marital_status": Employee.MaritalStatus.SINGLE,
            "plant": self.plant.pk,
            "department": self.dept.pk,
            "job_position": self.job.pk,
            "manager": self.manager_employee.pk,
            "join_date": self.today.isoformat(),
            "status": Employee.Status.PERMANENT,
        }
        data.update(overrides)
        return data

    def test_full_new_hire_workflow(self):
        # 1. HR registers employee (akun login di-link terpisah)
        self.client.login(username="hre2e", password="TestPassword123!")
        response = self.client.post(reverse("web:employee_create"), self._employee_form_data())
        self.assertEqual(response.status_code, 302, msg=response.content.decode()[:500])
        employee = Employee.objects.get(employee_id="P1-NEW")
        employee.user = self.new_user
        employee.save(update_fields=["user", "updated_at"])
        self.assertEqual(employee.user_id, self.new_user.pk)

        # 2. Leave quota + default shift provisioned on hire
        balance = LeaveBalance.objects.get(employee=employee, leave_type=self.leave_type)
        self.assertEqual(balance.remaining, Decimal("12"))
        assignment = ShiftAssignment.objects.get(employee=employee, work_date=self.today)
        self.assertEqual(assignment.shift_id, self.shift.pk)

        # 3. Employee clocks in/out with selfie (web punch)
        self.client.logout()
        self.client.login(username="newhire", password="TestPassword123!")
        photo = _sample_photo_data_url()
        response = self.client.post(reverse("web:punch"), {"action": "in", "photo": photo})
        self.assertEqual(response.status_code, 302)
        record = AttendanceRecord.objects.get(employee=employee, work_date=self.today)
        self.assertIsNotNone(record.check_in)

        response = self.client.post(reverse("web:punch"), {"action": "out", "photo": photo})
        self.assertEqual(response.status_code, 302)
        record.refresh_from_db()
        self.assertIsNotNone(record.check_out)

        # 4. Overtime requires approval — simulate late CO
        AttendanceRecord.objects.filter(pk=record.pk).delete()
        check_in_when = timezone.make_aware(datetime.combine(self.today, time(7, 0)), self.tz)
        check_out_when = timezone.make_aware(datetime.combine(self.today, time(17, 0)), self.tz)
        selfie_in = decode_selfie(photo)
        clock_in(employee, when=check_in_when, photo=selfie_in)
        selfie_out = decode_selfie(photo)
        clock_out(employee, when=check_out_when, photo=selfie_out)
        timesheet = DailyTimesheet.objects.get(employee=employee, work_date=self.today)
        self.assertEqual(timesheet.ot_after_minutes, 0)

        response = self.client.post(
            reverse("web:overtime_create"),
            {
                "overtime_type": self.overtime_type.pk,
                "work_date": self.today.isoformat(),
                "ot_after_minutes": "120",
                "reason": "Produksi tambahan",
            },
        )
        self.assertEqual(response.status_code, 302, msg=response.content.decode()[:500])
        overtime_req = OvertimeRequest.objects.get(employee=employee)
        self.assertEqual(overtime_req.status, OvertimeRequest.Status.PENDING)

        self.client.logout()
        self.client.login(username="hre2e", password="TestPassword123!")
        response = self.client.post(reverse("web:overtime_approve", args=[overtime_req.pk]))
        self.assertEqual(response.status_code, 302)
        timesheet.refresh_from_db()
        self.assertEqual(timesheet.ot_after_minutes, 120)

        # 5. Employee submits leave; HR approves
        self.client.logout()
        self.client.login(username="newhire", password="TestPassword123!")
        leave_start = self.today + timedelta(days=30)
        response = self.client.post(
            reverse("web:leave_create"),
            {
                "leave_type": self.leave_type.pk,
                "start_date": leave_start.isoformat(),
                "end_date": leave_start.isoformat(),
                "reason": "Cuti tahunan",
            },
        )
        self.assertEqual(response.status_code, 302, msg=response.content.decode()[:500])
        leave_req = LeaveRequest.objects.get(employee=employee)
        self.assertEqual(leave_req.status, LeaveRequest.Status.PENDING)

        self.client.logout()
        self.client.login(username="hre2e", password="TestPassword123!")
        response = self.client.post(reverse("web:leave_approve", args=[leave_req.pk]))
        self.assertEqual(response.status_code, 302)
        leave_req.refresh_from_db()
        self.assertEqual(leave_req.status, LeaveRequest.Status.APPROVED)

        balance.refresh_from_db()
        self.assertEqual(balance.used, Decimal("1"))
        self.assertEqual(balance.remaining, Decimal("11"))

    def test_mobile_api_punch_requires_and_accepts_photo(self):
        employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            job_position=self.job,
            employee_id="P1-API",
            full_name="API Tester",
            user=self.new_user,
        )
        self.api.force_authenticate(user=self.new_user)

        response = self.api.post("/api/v1/attendance/clock_in/", {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Foto selfie", response.data["detail"])

        response = self.api.post(
            "/api/v1/attendance/clock_in/",
            {"photo": _sample_photo_data_url()},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            AttendanceRecord.objects.filter(employee=employee, check_in__isnull=False).exists()
        )
