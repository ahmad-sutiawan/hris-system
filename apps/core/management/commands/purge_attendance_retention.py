from django.core.management.base import BaseCommand

from apps.attendance.services.retention import purge_attendance_data
from apps.core.models import Tenant


class Command(BaseCommand):
    help = "Purge attendance records older than 6 months and photos older than 1 month."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            help="Tenant slug (default: all tenants)",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="Actually delete data (default is dry-run).",
        )

    def handle(self, *args, **options):
        tenant = None
        if options.get("tenant"):
            tenant = Tenant.objects.filter(slug=options["tenant"]).first()
            if not tenant:
                self.stderr.write(self.style.ERROR(f"Tenant '{options['tenant']}' not found."))
                return

        dry_run = not options["execute"]
        stats = purge_attendance_data(tenant=tenant, dry_run=dry_run)
        mode = "DRY-RUN" if dry_run else "EXECUTED"
        self.stdout.write(
            self.style.SUCCESS(
                f"[{mode}] records={stats['records_to_delete']} "
                f"timesheets={stats['timesheets_to_delete']} "
                f"photos={stats['photos_cleared']}"
            )
        )
        if dry_run:
            self.stdout.write("Run with --execute to apply changes.")
