from django.core.management.base import BaseCommand

from apps.core.auth_login import apply_employee_credentials
from apps.core.models import User
from apps.employees.models import Employee
from apps.employees.nik_lookup import compute_nik_lookup


class Command(BaseCommand):
    help = (
        "Set login karyawan: username & password = Employee ID. "
        "Login bisa pakai NIK atau Employee ID. Admin tidak diubah."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            default=None,
            help="Slug tenant (default: semua tenant)",
        )

    def handle(self, *args, **options):
        qs = Employee.objects.select_related("user", "tenant").exclude(
            status__in=[Employee.Status.INACTIVE, Employee.Status.RESIGNED]
        )
        if options["tenant"]:
            qs = qs.filter(tenant__slug=options["tenant"])

        updated = 0
        skipped = 0
        for employee in qs.iterator():
            if not employee.employee_id:
                skipped += 1
                continue
            if employee.user and (
                employee.user.is_superuser or employee.user.role == User.Role.ADMIN
            ):
                skipped += 1
                continue

            role = employee.user.role if employee.user_id else User.Role.EMPLOYEE
            if employee.user and employee.user.role == User.Role.MANAGER:
                role = User.Role.MANAGER

            lookup = compute_nik_lookup(employee.nik or "")
            if lookup and employee.nik_lookup != lookup:
                employee.nik_lookup = lookup
                employee.save(update_fields=["nik_lookup", "updated_at"])

            user = apply_employee_credentials(employee, role=role)
            if user:
                updated += 1
                self.stdout.write(
                    f"  {employee.full_name}: login NIK/ID → password = {employee.employee_id}"
                )
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(f"Selesai — {updated} karyawan diperbarui, {skipped} dilewati."))
        self.stdout.write("Admin tetap pakai username admin (bukan NIK/ID).")
