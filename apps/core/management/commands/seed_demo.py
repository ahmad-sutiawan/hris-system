import os
from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.attendance.models import AttendanceCode, OvertimeType
from apps.core.models import Plant, Tenant, User
from apps.employees.models import Employee
from apps.leave.models import LeaveType
from apps.leave.services.leave_workflow import get_or_create_balance
from apps.organization.models import Department, JobPosition
from apps.payroll.services.ter import seed_ter_master
from apps.payroll.models import SalaryComponent
from apps.shifts.models import Shift, ShiftAssignment


class Command(BaseCommand):
    help = "Seed demo tenant, plant, master codes, and admin user"

    DEMO_PASSWORDS = {
        "admin": "Admin123456!",
        "manager": "Manager123!",
        "budi": "Employee123!",
        "ayub": "Employee123!",
    }

    def _ensure_demo_user(self, username, *, defaults):
        user, created = User.objects.get_or_create(username=username, defaults=defaults)
        password = self.DEMO_PASSWORDS[username]
        user.set_password(password)
        for field, value in defaults.items():
            setattr(user, field, value)
        user.save()
        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Created demo user ({username} / {password})")
            )
        return user

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
        if plant.latitude is None:
            plant.latitude = Decimal("-6.2088000")
            plant.longitude = Decimal("106.8456000")
            plant.geo_fence_radius_m = 200
            plant.save(update_fields=["latitude", "longitude", "geo_fence_radius_m"])
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

        Shift.objects.get_or_create(
            tenant=tenant,
            plant=plant,
            code="MALAM",
            defaults={
                "name": "Shift Malam",
                "label": "MALAM",
                "scheduled_check_in": time(22, 0),
                "scheduled_check_out": time(6, 0),
                "break_minutes": 60,
                "grace_period_minutes": 15,
                "schedule_working_hours": Decimal("8"),
                "cross_day": True,
                "shift_allowance_code": "MALAM",
            },
        )
        night_shift = Shift.objects.filter(tenant=tenant, plant=plant, code="MALAM").first()
        if night_shift and night_shift.shift_allowance_code != "MALAM":
            night_shift.shift_allowance_code = "MALAM"
            night_shift.save(update_fields=["shift_allowance_code"])

        if plant.default_shift_id != shift.pk:
            plant.default_shift = shift
            plant.save(update_fields=["default_shift"])

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

        overtime_types = [
            ("OT-HK-1", "Lembur Hari Kerja Jam I", OvertimeType.DayCategory.WORKDAY, 1, 1, Decimal("1.5")),
            ("OT-HK-2", "Lembur Hari Kerja Jam II+", OvertimeType.DayCategory.WORKDAY, 2, None, Decimal("2")),
            ("OT-L6-1", "Lembur Libur 6 Jam Pertama", OvertimeType.DayCategory.HOLIDAY_6H, 1, 6, Decimal("2")),
            ("OT-L6-2", "Lembur Libur Jam 7–8", OvertimeType.DayCategory.HOLIDAY_6H, 7, 8, Decimal("3")),
            ("OT-L6-3", "Lembur Libur Jam 9–10", OvertimeType.DayCategory.HOLIDAY_6H, 9, 10, Decimal("4")),
            ("OT-L8-1", "Lembur Libur ≤8 Jam", OvertimeType.DayCategory.HOLIDAY_8H, 1, 8, Decimal("2")),
            ("OT-L8-2", "Lembur Libur Jam 9", OvertimeType.DayCategory.HOLIDAY_8H, 9, 9, Decimal("3")),
            ("OT-L8-3", "Lembur Libur Jam 10", OvertimeType.DayCategory.HOLIDAY_8H, 10, 10, Decimal("4")),
        ]
        for code, name, category, hour_from, hour_to, multiplier in overtime_types:
            OvertimeType.objects.get_or_create(
                tenant=tenant,
                code=code,
                defaults={
                    "name": name,
                    "day_category": category,
                    "hour_from": hour_from,
                    "hour_to": hour_to,
                    "multiplier": multiplier,
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

        seed_ter_master(tenant)

        from apps.core.models import ApprovalLine, HolidayCalendar, PunchLocation
        from apps.organization.models import JobLevel
        from apps.payroll.models import ShiftAllowanceRate

        PunchLocation.objects.get_or_create(
            tenant=tenant,
            plant=plant,
            name="Kantor Hybrid BSD",
            defaults={
                "latitude": Decimal("-6.3014000"),
                "longitude": Decimal("106.6539000"),
                "radius_m": 150,
                "is_active": True,
            },
        )

        national_holidays_2026 = [
            (date(2026, 1, 1), "Tahun Baru"),
            (date(2026, 1, 29), "Imlek"),
            (date(2026, 3, 19), "Nyepi"),
            (date(2026, 4, 3), "Wafat Isa Almasih"),
            (date(2026, 4, 18), "Idul Fitri"),
            (date(2026, 5, 1), "Hari Buruh"),
            (date(2026, 5, 14), "Kenaikan Isa Almasih"),
            (date(2026, 5, 25), "Idul Adha"),
            (date(2026, 6, 1), "Pancasila"),
            (date(2026, 8, 17), "HUT RI"),
            (date(2026, 12, 25), "Natal"),
        ]
        for holiday_date, name in national_holidays_2026:
            HolidayCalendar.objects.get_or_create(
                tenant=tenant,
                holiday_date=holiday_date,
                name=name,
                defaults={
                    "holiday_type": HolidayCalendar.HolidayType.NATIONAL,
                    "is_active": True,
                },
            )

        job_levels = [
            (1, "LEADER", "Leader"),
            (2, "ANGGOTA", "Anggota"),
            (3, "STAFF", "Staff"),
            (4, "SR_STAFF", "Sr Staff"),
            (5, "JR_SUP", "Jr Supervisor"),
            (6, "SUP", "Supervisor"),
            (7, "ASST_MGR", "Assistant Manager"),
            (8, "MGR", "Manager"),
            (9, "HEAD", "Head"),
            (10, "DIR", "Direktur"),
        ]
        for rank, code, name in job_levels:
            JobLevel.objects.get_or_create(
                tenant=tenant,
                code=code,
                defaults={"name": name, "rank": rank},
            )

        for request_type in (
            ApprovalLine.RequestType.LEAVE,
            ApprovalLine.RequestType.OVERTIME,
            ApprovalLine.RequestType.ATTENDANCE_CORRECTION,
        ):
            ApprovalLine.objects.get_or_create(
                tenant=tenant,
                request_type=request_type,
                step_order=1,
                defaults={"approver_kind": ApprovalLine.ApproverKind.DIRECT_MANAGER},
            )
            ApprovalLine.objects.get_or_create(
                tenant=tenant,
                request_type=request_type,
                step_order=2,
                defaults={"approver_kind": ApprovalLine.ApproverKind.HR_PLANT},
            )

        ShiftAllowanceRate.objects.get_or_create(
            tenant=tenant,
            code="MALAM",
            defaults={
                "name": "Tunjangan Shift Malam",
                "amount": Decimal("50000"),
            },
        )

        admin_user = self._ensure_demo_user(
            "admin",
            defaults={
                "email": "admin@hris.local",
                "is_staff": True,
                "is_superuser": True,
                "tenant": tenant,
                "plant": plant,
                "role": User.Role.ADMIN,
            },
        )

        mgr_user = self._ensure_demo_user(
            "manager",
            defaults={
                "email": "manager@demo.local",
                "tenant": tenant,
                "plant": plant,
                "role": User.Role.MANAGER,
            },
        )

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
                "salary_scheme": Employee.SalaryScheme.DAILY,
                "base_salary": Decimal("200000"),
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

        emp_user = self._ensure_demo_user(
            "budi",
            defaults={
                "email": "budi@demo.local",
                "tenant": tenant,
                "plant": plant,
                "role": User.Role.EMPLOYEE,
            },
        )
        if not employee.user_id:
            employee.user = emp_user
            employee.save(update_fields=["user"])

        ayub_user = self._ensure_demo_user(
            "ayub",
            defaults={
                "tenant": tenant,
                "plant": plant,
                "role": User.Role.EMPLOYEE,
            },
        )

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

        from apps.employees.services.mandatory_defaults import backfill_all_employees

        backfill_all_employees(tenant=tenant)

        self.stdout.write(self.style.SUCCESS(f"Seed complete for tenant '{tenant.slug}'"))
