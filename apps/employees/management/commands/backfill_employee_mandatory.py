from django.core.management.base import BaseCommand

from apps.core.models import Tenant
from apps.employees.services.mandatory_defaults import backfill_all_employees


class Command(BaseCommand):
    help = "Isi field mandatory karyawan yang kosong dengan nilai default N/A."

    def add_arguments(self, parser):
        parser.add_argument("--tenant", help="Slug tenant (default: semua tenant)")

    def handle(self, *args, **options):
        tenant = None
        if options.get("tenant"):
            tenant = Tenant.objects.filter(slug=options["tenant"]).first()
            if not tenant:
                self.stderr.write(self.style.ERROR(f"Tenant '{options['tenant']}' tidak ditemukan."))
                return

        stats = backfill_all_employees(tenant=tenant)
        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill selesai: {stats['updated']} dari {stats['total']} karyawan diperbarui."
            )
        )
