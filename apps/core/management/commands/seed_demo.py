import os
from datetime import time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.attendance.models import AttendanceCode
from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.leave.models import LeaveType
from apps.leave.services.leave_workflow import get_or_create_balance
from apps.organization.models import Department, JobPosition, LegalEntity
from apps.payroll.models import SalaryComponent
from apps.shifts.models import Shift, ShiftAssignment


class Command(BaseCommand):
    help = "Seed demo tenant, plant, master codes, and admin user"

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(
            slug=os.environ.get("HRIS_DEFAULT_TENANT_SLUG", "default"),
            defaults={"name": "Demo Manufacturing Co."},
        )
        plant, _ = Plant.objects.get_or_create(
            tenant=tenant,
            code="PLT01",
            defaults={"name": "Plant Utama"},
        )
        LegalEntity.objects.get_or_create(
            tenant=tenant,
            name="PT Demo Manufaktur",
            defaults={"npwp": "00.000.000.0-000.000"},
        )
        dept, _ = Department.objects.get_or_create(
            tenant=tenant,
            plant=plant,
            code="PROD",
            defaults={"name": "Production"},
        )
        job, _ = JobPosition.objects.get_or_create(
            tenant=tenant,
            plant=plant,
            code="OPR",
            defaults={"title": "Operator", "department": dept},
        )

        shift, _ = Shift.objects.get_or_create(
            tenant=tenant,
            plant=plant,
            code="PAGI",
            defaults={
                "name": "Shift Pagi",
                "label": "PAGI",
                "scheduled_check_in": time(7, 0),
                "scheduled_check_out": time(15, 0),
                "break_minutes": 60,
                "grace_period_minutes": 15,
                "schedule_working_hours": Decimal("8"),
            },
        )

        attendance_codes = [
            ("H", "Hadir", AttendanceCode.PayrollImpact.PAID),
            ("A", "Alpha", AttendanceCode.PayrollImpact.UNPAID),
            ("I", "Izin", AttendanceCode.PayrollImpact.NONE),
            ("S", "Sakit", AttendanceCode.PayrollImpact.PAID),
            ("C", "Cuti", AttendanceCode.PayrollImpact.NONE),
            ("L", "Libur", AttendanceCode.PayrollImpact.NONE),
        ]
        for code, label, impact in attendance_codes:
            AttendanceCode.objects.get_or_create(
                tenant=tenant,
                code=code,
                defaults={"label": label, "payroll_impact": impact},
            )

        leave_types = [
            ("CT", "Cuti Tahunan", True, 12),
            ("CS", "Cuti Sakit", True, 0),
            ("A", "Alpha", False, 0),
        ]
        for code, name, is_paid, quota in leave_types:
            LeaveType.objects.get_or_create(
                tenant=tenant,
                code=code,
                defaults={
                    "name": name,
                    "is_paid": is_paid,
                    "default_quota_days": quota,
                },
            )

        components = [
            ("BASE", "Gaji Pokok", SalaryComponent.ComponentType.EARNING),
            ("OT_AFTER", "Lembur", SalaryComponent.ComponentType.EARNING),
            ("BPJS_KES", "BPJS Kesehatan", SalaryComponent.ComponentType.DEDUCTION),
            ("PPh21", "PPh 21", SalaryComponent.ComponentType.DEDUCTION),
        ]
        for code, name, ctype in components:
            SalaryComponent.objects.get_or_create(
                tenant=tenant,
                code=code,
                defaults={"name": name, "component_type": ctype},
            )

        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@hris.local",
                "is_staff": True,
                "is_superuser": True,
                "tenant": tenant,
                "plant": plant,
                "role": User.Role.ADMIN,
            },
        )
        if created:
            admin_user.set_password("Admin123456!")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("Created admin user (admin / Admin123456!)"))

        mgr_user, created = User.objects.get_or_create(
            username="manager",
            defaults={
                "email": "manager@demo.local",
                "tenant": tenant,
                "plant": plant,
                "role": User.Role.MANAGER,
            },
        )
        if created:
            mgr_user.set_password("Manager123!")
            mgr_user.save()
            self.stdout.write(self.style.SUCCESS("Created manager user (manager / Manager123!)"))

        manager_employee, _ = Employee.objects.update_or_create(
            tenant=tenant,
            employee_id="PLT01-2026-MGR",
            defaults={
                "plant": plant,
                "department": dept,
                "job_position": job,
                "full_name": "Siti Manager",
                "email": "manager@demo.local",
                "join_date": timezone.localdate(),
                "status": Employee.Status.PERMANENT,
                "base_salary": Decimal("8000000"),
                "user": mgr_user,
            },
        )
        if not manager_employee.user_id:
            manager_employee.user = mgr_user
            manager_employee.save(update_fields=["user"])

        employee, _ = Employee.objects.update_or_create(
            tenant=tenant,
            employee_id="PLT01-2026-001",
            defaults={
                "plant": plant,
                "department": dept,
                "job_position": job,
                "manager": manager_employee,
                "full_name": "Budi Santoso",
                "nik": "3201010101900001",
                "email": "budi@demo.local",
                "join_date": timezone.localdate(),
                "status": Employee.Status.PERMANENT,
                "base_salary": Decimal("5000000"),
                "allowance_transport": Decimal("500000"),
                "tax_status": "TK/0",
                "bank_name": "BCA",
                "bank_account_number": "9876543210",
                "bank_account_name": "Budi Santoso",
            },
        )

        ct = LeaveType.objects.get(tenant=tenant, code="CT")
        get_or_create_balance(employee, ct)

        today = timezone.localdate()
        ShiftAssignment.objects.get_or_create(
            tenant=tenant,
            employee=employee,
            work_date=today,
            defaults={
                "shift": shift,
                "scheduled_check_in": shift.scheduled_check_in,
                "scheduled_check_out": shift.scheduled_check_out,
            },
        )

        emp_user, created = User.objects.get_or_create(
            username="budi",
            defaults={
                "email": "budi@demo.local",
                "tenant": tenant,
                "plant": plant,
                "role": User.Role.EMPLOYEE,
            },
        )
        if created:
            emp_user.set_password("Employee123!")
            emp_user.save()
            self.stdout.write(self.style.SUCCESS("Created employee user (budi / Employee123!)"))
        if not employee.user_id:
            employee.user = emp_user
            employee.save(update_fields=["user"])

        ayub_user, created = User.objects.get_or_create(
            username="ayub",
            defaults={
                "tenant": tenant,
                "plant": plant,
                "role": User.Role.EMPLOYEE,
            },
        )
        if created:
            ayub_user.set_password("Employee123!")
            ayub_user.save()
            self.stdout.write(self.style.SUCCESS("Created employee user (ayub / Employee123!)"))

        ayub_employee, _ = Employee.objects.update_or_create(
            tenant=tenant,
            employee_id="PLT01-2026-002",
            defaults={
                "plant": plant,
                "department": dept,
                "job_position": job,
                "manager": manager_employee,
                "full_name": "Ayub",
                "join_date": timezone.localdate(),
                "status": Employee.Status.PERMANENT,
                "base_salary": Decimal("5000000"),
                "user": ayub_user,
            },
        )
        if not ayub_employee.user_id:
            ayub_employee.user = ayub_user
            ayub_employee.save(update_fields=["user"])
        get_or_create_balance(ayub_employee, ct)

        self.stdout.write(self.style.SUCCESS(f"Seed complete for tenant '{tenant.slug}'"))
