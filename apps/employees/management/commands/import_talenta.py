from pathlib import Path

from django.core.management.base import BaseCommand

from apps.core.models import Tenant
from apps.employees.services.import_talenta import import_employees_talenta_xlsx


class Command(BaseCommand):
    help = "Import karyawan dari file export Excel Talenta (.xlsx)."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path file .xlsx export Talenta")
        parser.add_argument("--tenant", required=True, help="Slug tenant tujuan")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Hitung baris tanpa menyimpan ke database.",
        )

    def handle(self, *args, **options):
        tenant = Tenant.objects.filter(slug=options["tenant"]).first()
        if not tenant:
            self.stderr.write(self.style.ERROR(f"Tenant '{options['tenant']}' tidak ditemukan."))
            return

        path = Path(options["path"])
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"File '{path}' tidak ditemukan."))
            return

        result = import_employees_talenta_xlsx(
            tenant,
            path.read_bytes(),
            dry_run=options["dry_run"],
        )

        prefix = "[DRY-RUN] " if options["dry_run"] else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}Import selesai: {result['created']} baru, {result['updated']} diupdate."
            )
        )
        self.stdout.write(
            "Master dibuat: "
            f"{result.get('plants_created', 0)} plant, "
            f"{result.get('departments_created', 0)} departemen, "
            f"{result.get('job_positions_created', 0)} role, "
            f"{result.get('job_levels_created', 0)} job level."
        )
        if result.get("managers_linked"):
            self.stdout.write(f"Atasan terhubung: {result['managers_linked']}")
        for warning in result.get("manager_warnings", []):
            self.stdout.write(self.style.WARNING(warning))
        if result["errors"]:
            self.stderr.write(self.style.WARNING(f"{len(result['errors'])} baris gagal:"))
            for err in result["errors"][:20]:
                self.stderr.write(f"  {err}")
