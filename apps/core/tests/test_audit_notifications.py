from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.core.models import AuditLog, Notification, Plant, Tenant, User
from apps.core.services.notifications import create_notification, mark_notifications_read, notify_user
from apps.employees.models import Employee
from apps.leave.models import LeaveRequest, LeaveType
from apps.leave.services.leave_workflow import (
    approve_leave_request,
    submit_leave_request,
)
from apps.organization.models import Department, JobPosition


class AuditNotificationTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(slug="test", name="Test Co")
        self.plant = Plant.objects.create(tenant=self.tenant, code="P1", name="Plant 1")
        self.dept = Department.objects.create(
            tenant=self.tenant, plant=self.plant, code="HR", name="HR"
        )
        self.job = JobPosition.objects.create(
            tenant=self.tenant, plant=self.plant, code="MGR", title="Manager", department=self.dept
        )
        self.manager_user = User.objects.create_user(
            username="mgr",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.MANAGER,
            email="mgr@test.local",
        )
        self.manager = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            job_position=self.job,
            employee_id="P1-MGR",
            full_name="Manager One",
            user=self.manager_user,
            base_salary=Decimal("7000000"),
        )
        self.employee_user = User.objects.create_user(
            username="emp",
            password="TestPassword123!",
            tenant=self.tenant,
            plant=self.plant,
            role=User.Role.EMPLOYEE,
            email="emp@test.local",
        )
        self.employee = Employee.objects.create(
            tenant=self.tenant,
            plant=self.plant,
            department=self.dept,
            job_position=self.job,
            manager=self.manager,
            employee_id="P1-001",
            full_name="Employee One",
            user=self.employee_user,
            base_salary=Decimal("5000000"),
        )
        self.leave_type = LeaveType.objects.create(
            tenant=self.tenant,
            code="CT",
            name="Cuti Tahunan",
            default_quota_days=12,
        )

    def test_employee_update_creates_audit_log(self):
        self.employee.full_name = "Employee Updated"
        self.employee.save()
        log = AuditLog.objects.filter(model_name="employees.employee", action=AuditLog.Action.UPDATE).first()
        self.assertIsNotNone(log)
        self.assertIn("full_name", log.changes)

    def test_notify_user_creates_notification(self):
        notify_user(
            tenant=self.tenant,
            user=self.manager_user,
            category=Notification.Category.LEAVE,
            title="Test",
            message="Hello",
            send_email=False,
        )
        self.assertEqual(
            Notification.objects.filter(user=self.manager_user, title="Test").count(),
            1,
        )

    def test_mark_notifications_read(self):
        n1 = create_notification(
            tenant=self.tenant,
            user=self.manager_user,
            category=Notification.Category.SYSTEM,
            title="A",
            message="A",
        )
        create_notification(
            tenant=self.tenant,
            user=self.manager_user,
            category=Notification.Category.SYSTEM,
            title="B",
            message="B",
        )
        mark_notifications_read(self.manager_user, [n1.pk])
        n1.refresh_from_db()
        self.assertTrue(n1.is_read)
        self.assertEqual(
            Notification.objects.filter(user=self.manager_user, is_read=False).count(),
            1,
        )

    @override_settings(HRIS_SITE_URL="http://testserver")
    def test_leave_submit_notifies_manager(self):
        start = timezone.localdate() + timedelta(days=7)
        end = start + timedelta(days=1)
        submit_leave_request(
            employee=self.employee,
            leave_type=self.leave_type,
            start_date=start,
            end_date=end,
            reason="Liburan",
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.manager_user,
                category=Notification.Category.LEAVE,
                title="Pengajuan cuti baru",
            ).exists()
        )

    @override_settings(HRIS_SITE_URL="http://testserver")
    def test_leave_approve_marks_manager_notification_read(self):
        start = timezone.localdate() + timedelta(days=10)
        leave_req = submit_leave_request(
            employee=self.employee,
            leave_type=self.leave_type,
            start_date=start,
            end_date=start,
            reason="Cuti",
        )
        notif = Notification.objects.get(
            user=self.manager_user,
            title="Pengajuan cuti baru",
        )
        self.assertFalse(notif.is_read)
        self.assertIn(f"req={leave_req.pk}", notif.link)

        approve_leave_request(leave_req, self.manager_user)

        notif.refresh_from_db()
        self.assertTrue(notif.is_read)
        self.assertEqual(
            Notification.objects.filter(
                user=self.manager_user,
                category=Notification.Category.LEAVE,
                is_read=False,
            ).count(),
            0,
        )
