"""Tahap 6 — multi-layer approval, shift allowance payroll, face check POC."""

from datetime import date, datetime, time
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from apps.attendance.models import DailyTimesheet
from apps.attendance.services.correction import apply_attendance_correction
from apps.attendance.services.face_check import FaceCheckError, validate_selfie_face
from apps.core.approval import can_approve_request
from apps.core.models import ApprovalLine, AuditLog, Plant, Tenant, User
from apps.employees.models import Employee
from apps.leave.models import LeaveRequest, LeaveType
from apps.leave.services.leave_workflow import (
    LeaveError,
    approve_leave_request,
    submit_leave_request,
)
from apps.organization.models import Department
from apps.payroll.models import ShiftAllowanceRate
from apps.payroll.services.shift_allowance import bulk_shift_allowance_pay
from apps.shifts.models import Shift


def _valid_selfie():
    buf = BytesIO()
    Image.new("RGB", (400, 400), color=(200, 180, 160)).save(buf, format="JPEG")
    return SimpleUploadedFile("selfie.jpg", buf.getvalue(), content_type="image/jpeg")


def _hat_selfie():
    img = Image.new("RGB", (400, 400))
    pixels = img.load()
    for y in range(400):
        for x in range(400):
            if y < 140:
                pixels[x, y] = (20, 20, 20)
            else:
                pixels[x, y] = (160 + (x * 7 + y * 11) % 60, 130 + (x * 3) % 40, 110 + (y * 5) % 35)
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return SimpleUploadedFile("hat.jpg", buf.getvalue(), content_type="image/jpeg")


@override_settings(ALLOWED_HOSTS=["testserver"])
class MultiLayerLeaveApprovalTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="t6", name="T6 Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.dept = Department.objects.create(
            tenant=self.tenant, plant=self.plant, code="HR", name="HR"
        )
        self.leave_type = LeaveType.objects.create(
            tenant=self.tenant, code="CT", name="Cuti Tahunan", default_quota_days=12
        )
        ApprovalLine.objects.create(
            tenant=self.tenant,
            request_type=ApprovalLine.RequestType.LEAVE,
            step_order=1,
            approver_kind=ApprovalLine.ApproverKind.DIRECT_MANAGER,
        )
        ApprovalLine.objects.create(
            tenant=self.tenant,
            request_type=ApprovalLine.RequestType.LEAVE,
            step_order=2,
            approver_kind=ApprovalLine.ApproverKind.HR_PLANT,
        )
        self.mgr_user = User.objects.create_user(
            username="t6mgr",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.MANAGER,
        )
        self.hr_user = User.objects.create_user(
            username="t6hr",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.HR,
        )
        self.manager = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            employee_id="MGR",
            full_name="Manager",
            join_date=date(2024, 1, 1),
            user=self.mgr_user,
        )
        self.worker = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            employee_id="E001",
            full_name="Worker",
            manager=self.manager,
            join_date=date(2024, 1, 1),
        )
        self.leave_req = submit_leave_request(
            employee=self.worker,
            leave_type=self.leave_type,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 2),
            reason="Liburan",
        )

    def test_hr_cannot_approve_before_manager(self):
        self.assertFalse(
            can_approve_request(self.hr_user, self.worker, "leave", self.leave_req.approval_step)
        )
        with self.assertRaises(LeaveError):
            approve_leave_request(self.leave_req, self.hr_user)

    def test_manager_then_hr_approves(self):
        approve_leave_request(self.leave_req, self.mgr_user)
        self.leave_req.refresh_from_db()
        self.assertEqual(self.leave_req.status, LeaveRequest.Status.PENDING)
        self.assertEqual(self.leave_req.approval_step, 2)
        self.assertTrue(
            can_approve_request(self.hr_user, self.worker, "leave", self.leave_req.approval_step)
        )
        approve_leave_request(self.leave_req, self.hr_user)
        self.leave_req.refresh_from_db()
        self.assertEqual(self.leave_req.status, LeaveRequest.Status.APPROVED)


@override_settings(ALLOWED_HOSTS=["testserver"])
class ShiftAllowancePayrollTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="t6pay", name="T6 Pay")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant")
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="E1",
            full_name="Shift Worker",
            join_date=date(2024, 1, 1),
        )
        self.shift = Shift.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="MALAM",
            name="Malam",
            scheduled_check_in=time(22, 0),
            scheduled_check_out=time(6, 0),
            cross_day=True,
            shift_allowance_code="MALAM",
        )
        ShiftAllowanceRate.objects.create(
            tenant=self.tenant,
            code="MALAM",
            name="Tunjangan Malam",
            amount=Decimal("50000"),
        )
        tz = timezone.get_current_timezone()
        for day in (1, 2, 3):
            work_date = date(2026, 6, day)
            DailyTimesheet.objects.create(
                tenant=self.tenant,
                plant=self.plant,
                employee=self.employee,
                work_date=work_date,
                shift=self.shift,
                check_in=timezone.make_aware(datetime.combine(work_date, time(22, 0)), tz),
            )

    def test_shift_allowance_totals(self):
        result = bulk_shift_allowance_pay(
            [self.employee.pk],
            date(2026, 6, 1),
            date(2026, 6, 30),
            tenant=self.tenant,
        )
        total, breakdown = result[self.employee.pk]
        self.assertEqual(total, Decimal("150000.00"))
        self.assertIn("shift_allowance_malam", breakdown)


@override_settings(ALLOWED_HOSTS=["testserver"])
class FaceCheckPocTests(TestCase):
    def test_valid_selfie_passes(self):
        validate_selfie_face(_valid_selfie())

    def test_hat_selfie_rejected(self):
        with self.assertRaises(FaceCheckError) as ctx:
            validate_selfie_face(_hat_selfie())
        self.assertIn("topi", str(ctx.exception).lower())


@override_settings(ALLOWED_HOSTS=["testserver"])
class CorrectionAuditTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="t6aud", name="T6 Aud")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant")
        self.admin = User.objects.create_user(
            username="t6admin",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.ADMIN,
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee_id="E1",
            full_name="Worker",
            join_date=date(2024, 1, 1),
        )
        self.shift = Shift.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            code="PAGI",
            name="Pagi",
            scheduled_check_in=time(7, 0),
            scheduled_check_out=time(15, 0),
        )

    def test_correction_audit_includes_actor(self):
        ts = DailyTimesheet.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            employee=self.employee,
            work_date=date(2026, 6, 10),
        )
        apply_attendance_correction(
            ts,
            check_in_time=time(7, 5),
            check_out_time=time(15, 0),
            shift=self.shift,
            actor=self.admin,
        )
        log = AuditLog.objects.filter(model_name="attendance.attendancerecord").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.changes.get("corrected_by"), "t6admin")
