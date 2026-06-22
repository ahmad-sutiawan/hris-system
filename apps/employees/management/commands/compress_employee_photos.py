"""Batch compress employee profile photos on server (setelah deploy / sync media)."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.employees.models import Employee
from apps.employees.services.photo import compress_employee_photo
from apps.organization.models import Tenant


class Command(BaseCommand):
    help = "Compress employee profile photos to WebP and report missing files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            default="default",
            help="Tenant slug (default: default)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Hanya laporan, tanpa mengubah file",
        )

    def handle(self, *args, **options):
        tenant_slug = options["tenant"]
        dry_run = options["dry_run"]

        tenant = Tenant.objects.filter(slug=tenant_slug).first()
        if not tenant:
            self.stderr.write(self.style.ERROR(f"Tenant '{tenant_slug}' tidak ditemukan."))
            return

        qs = Employee.objects.filter(tenant=tenant).exclude(photo="").exclude(photo__isnull=True)
        total = qs.count()
        compressed = 0
        missing = 0
        skipped = 0

        self.stdout.write(f"Tenant {tenant_slug}: {total} karyawan punya path foto di database")

        for employee in qs.iterator():
            path = employee.photo.name
            full = Path(settings.MEDIA_ROOT) / path
            if not full.is_file():
                missing += 1
                self.stdout.write(self.style.WARNING(f"  MISSING file: {employee.employee_id} → {path}"))
                continue

            if path.lower().endswith(".webp"):
                skipped += 1
                continue

            if dry_run:
                self.stdout.write(f"  would compress: {employee.employee_id} → {path}")
                compressed += 1
                continue

            before = path
            compress_employee_photo(employee)
            if employee.photo.name != before:
                employee.save(update_fields=["photo"])
                compressed += 1
                self.stdout.write(f"  compressed: {employee.employee_id} → {employee.photo.name}")
            else:
                skipped += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Selesai — total={total}, compressed={compressed}, "
                f"already_webp={skipped}, missing_file={missing}"
            )
        )
        if missing:
            self.stdout.write(
                self.style.WARNING(
                    "Ada foto di database tapi file tidak ada di volume media. "
                    "Upload ulang via web HRIS atau sync folder media/ ke server."
                )
            )
