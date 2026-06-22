"""Quick deployment diagnostics — tenant, users, employees, encryption sample."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.core.encryption import decrypt_value
from apps.core.models import Tenant
from apps.employees.models import Employee

User = get_user_model()


class Command(BaseCommand):
    help = "Cek kesiapan deploy: tenant, user, karyawan, dan sampel dekripsi."

    def handle(self, *args, **options):
        tenants = Tenant.objects.count()
        users = User.objects.filter(is_active=True).count()
        employees = Employee.objects.count()
        self.stdout.write(f"Tenants: {tenants}")
        self.stdout.write(f"Active users: {users}")
        self.stdout.write(f"Employees: {employees}")

        if tenants == 0:
            self.stdout.write(self.style.ERROR("Tidak ada tenant — import data atau provision tenant default."))
        if users == 0:
            self.stdout.write(self.style.ERROR("Tidak ada user — jalankan sync_employee_credentials atau bootstrap superuser."))

        sample = (
            Employee.objects.exclude(nik="")
            .values_list("nik", flat=True)
            .first()
        )
        if sample:
            if str(sample).startswith("enc:v1:"):
                plain = decrypt_value(sample)
                if plain:
                    self.stdout.write(self.style.SUCCESS("Dekripsi NIK sample: OK"))
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            "Dekripsi NIK gagal — HRIS_FIELD_ENCRYPTION_KEY tidak cocok dengan data DB."
                        )
                    )
            else:
                self.stdout.write("Sample NIK belum terenkripsi (plain text).")
        else:
            self.stdout.write("Belum ada data karyawan dengan NIK.")
