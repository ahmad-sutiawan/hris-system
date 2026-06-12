import gzip
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import AuditLog


class Command(BaseCommand):
    help = (
        "Arsipkan audit log lebih lama dari retention ke file JSONL.gz, "
        "lalu hapus dari DB (batch) agar tabel tidak membengkak."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=getattr(settings, "HRIS_AUDIT_RETENTION_DAYS", 365),
            help="Simpan log dalam N hari terakhir di DB (default: HRIS_AUDIT_RETENTION_DAYS).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=getattr(settings, "HRIS_AUDIT_ARCHIVE_BATCH_SIZE", 5000),
            help="Jumlah baris per batch ekspor/hapus.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Ekspor ke file arsip tanpa menghapus dari database.",
        )
        parser.add_argument(
            "--tenant-slug",
            type=str,
            default="",
            help="Batasi ke satu tenant (opsional).",
        )

    def handle(self, *args, **options):
        retention_days = options["days"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]
        tenant_slug = options["tenant_slug"]

        cutoff = timezone.now() - timezone.timedelta(days=retention_days)
        base_qs = AuditLog.objects.filter(created_at__lt=cutoff).order_by("created_at")
        if tenant_slug:
            base_qs = base_qs.filter(tenant__slug=tenant_slug)

        total = base_qs.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("Tidak ada audit log yang perlu diarsipkan."))
            return

        archive_dir = Path(getattr(settings, "HRIS_AUDIT_ARCHIVE_DIR", settings.BASE_DIR / "audit_archive"))
        archive_dir.mkdir(parents=True, exist_ok=True)
        stamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        tenant_part = tenant_slug or "all"
        archive_path = archive_dir / f"audit_{tenant_part}_{stamp}.jsonl.gz"

        archived = 0
        value_fields = (
            "id",
            "tenant_id",
            "user_id",
            "action",
            "model_name",
            "object_id",
            "object_repr",
            "changes",
            "ip_address",
            "user_agent",
            "integrity_hash",
            "created_at",
        )

        with gzip.open(archive_path, "wt", encoding="utf-8") as handle:
            if dry_run:
                for row in base_qs.values(*value_fields).iterator(chunk_size=batch_size):
                    row = dict(row)
                    row["created_at"] = row["created_at"].isoformat()
                    handle.write(json.dumps(row, default=str) + "\n")
                    archived += 1
            else:
                while base_qs.exists():
                    batch = list(base_qs.values(*value_fields)[:batch_size])
                    if not batch:
                        break
                    for row in batch:
                        row["created_at"] = row["created_at"].isoformat()
                        handle.write(json.dumps(row, default=str) + "\n")
                    archived += len(batch)
                    ids = [row["id"] for row in batch]
                    AuditLog.objects.filter(pk__in=ids)._raw_delete(base_qs.db)

        self.stdout.write(
            self.style.SUCCESS(
                f"{'[DRY-RUN] ' if dry_run else ''}Arsipkan {archived} dari {total} audit log ke {archive_path}"
            )
        )
        if dry_run:
            self.stdout.write(self.style.NOTICE("Dry-run: tidak ada baris yang dihapus dari database."))
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Log lebih lama dari {retention_days} hari dihapus dari DB. "
                    "Jadwalkan perintah ini bulanan (cron)."
                )
            )
