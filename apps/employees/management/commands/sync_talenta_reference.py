from django.core.management.base import BaseCommand

from apps.core.models import Tenant
from apps.employees.services.import_talenta import import_employees_talenta_xlsx
from apps.employees.services.talenta_reference import find_talenta_excel_file


class Command(BaseCommand):
    help = "Sinkronkan master data & karyawan dari file Excel Talenta di folder media."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            required=True,
            help="Slug tenant tujuan",
        )
        parser.add_argument(
            "--path",
            help="Path file .xlsx (default: file Talenta terbaru di MEDIA_ROOT)",
        )
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

        if options["path"]:
            from pathlib import Path

            path = Path(options["path"])
            if not path.exists():
                self.stderr.write(self.style.ERROR(f"File '{path}' tidak ditemukan."))
                return
            content = path.read_bytes()
            source = str(path)
        else:
            path = find_talenta_excel_file()
            if not path:
                self.stderr.write(
                    self.style.ERROR(
                        "Tidak ada file export Talenta (.xlsx) di folder media. "
                        "Upload file Excel ke media/ terlebih dahulu."
                    )
                )
                return
            content = path.read_bytes()
            source = str(path)

        self.stdout.write(f"Sumber: {source}")

        result = import_employees_talenta_xlsx(
            tenant,
            content,
            dry_run=options["dry_run"],
        )

        prefix = "[DRY-RUN] " if options["dry_run"] else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}Sync selesai: {result['created']} baru, {result['updated']} diupdate."
            )
        )
        self.stdout.write(
            "Master: "
            f"{result.get('plants_created', 0)} branch, "
            f"{result.get('departments_created', 0)} organization, "
            f"{result.get('job_positions_created', 0)} job position, "
            f"{result.get('job_levels_created', 0)} job level."
        )
        if result.get("managers_linked"):
            self.stdout.write(f"Manager terhubung: {result['managers_linked']}")
        for warning in result.get("manager_warnings", []):
            self.stdout.write(self.style.WARNING(warning))
        if result["errors"]:
            self.stderr.write(self.style.WARNING(f"{len(result['errors'])} baris gagal:"))
            for err in result["errors"][:20]:
                self.stderr.write(f"  {err}")
