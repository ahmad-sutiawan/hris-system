"""Perbaikan deploy production — tenant, admin, kredensial karyawan, cek enkripsi."""

import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.core.encryption import decrypt_value
from apps.core.models import Tenant
from apps.employees.models import Employee

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Perbaiki login production: cek tenant/user, dekripsi, sync kredensial, "
        "opsional buat superuser."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            default=os.environ.get("HRIS_DEFAULT_TENANT_SLUG", "default"),
            help="Slug tenant (default: default)",
        )
        parser.add_argument(
            "--bootstrap-admin",
            action="store_true",
            help="Buat/perbarui superuser admin jika belum ada user aktif",
        )
        parser.add_argument(
            "--admin-password",
            default=os.environ.get("HRIS_ADMIN_PASSWORD", "Admin123456!"),
            help="Password superuser saat --bootstrap-admin",
        )
        parser.add_argument(
            "--sync-credentials",
            action="store_true",
            help="Sinkronkan login karyawan (default: tidak, agar data tidak diubah)",
        )

    def handle(self, *args, **options):
        tenant_slug = options["tenant"]
        tenants = Tenant.objects.count()
        users = User.objects.filter(is_active=True).count()
        employees = Employee.objects.count()

        self.stdout.write(f"Tenants: {tenants}")
        self.stdout.write(f"Active users: {users}")
        self.stdout.write(f"Employees: {employees}")

        if tenants == 0:
            tenant, created = Tenant.objects.get_or_create(
                slug=tenant_slug,
                defaults={"name": tenant_slug.upper()},
            )
            action = "dibuat" if created else "ada"
            self.stdout.write(self.style.WARNING(f"Tenant {tenant.slug} {action}."))
        else:
            tenant = Tenant.objects.filter(slug=tenant_slug).first()
            if not tenant:
                tenant = Tenant.objects.order_by("pk").first()
                self.stdout.write(
                    self.style.WARNING(
                        f"Tenant '{tenant_slug}' tidak ada — pakai tenant pertama: {tenant.slug}"
                    )
                )

        enc_ok = self._check_encryption()
        if not enc_ok:
            self.stdout.write(
                self.style.ERROR(
                    "HRIS_FIELD_ENCRYPTION_KEY tidak cocok dengan data karyawan di server."
                )
            )

        if options["bootstrap_admin"] or users == 0:
            call_command(
                "ensure_superuser",
                tenant=tenant.slug,
                password=options["admin_password"],
            )

        if options["sync_credentials"] and employees > 0:
            call_command("sync_employee_credentials", tenant=tenant.slug)

        self.stdout.write(self.style.SUCCESS("repair_production selesai."))
        if users == 0 and employees == 0:
            self.stdout.write(
                "Database kosong — import dump bps_hris ke MySQL container, "
                "lalu jalankan perintah ini lagi."
            )

    def _check_encryption(self) -> bool:
        sample = Employee.objects.exclude(nik="").values_list("nik", flat=True).first()
        if not sample:
            self.stdout.write("Belum ada NIK terenkripsi — lewati cek dekripsi.")
            return True
        if not str(sample).startswith("enc:v1:"):
            self.stdout.write("Sample NIK plain text — OK untuk DB baru.")
            return True
        plain = decrypt_value(sample)
        if plain:
            self.stdout.write(self.style.SUCCESS("Dekripsi NIK sample: OK"))
            return True
        self.stdout.write(self.style.ERROR("Dekripsi NIK sample: GAGAL"))
        return False
