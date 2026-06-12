import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Backup database MySQL via mysqldump (production cron harian)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            type=str,
            default=str(Path(settings.BASE_DIR) / "backups"),
        )

    def handle(self, *args, **options):
        db = settings.DATABASES["default"]
        engine = db.get("ENGINE", "")
        if "mysql" not in engine:
            self.stderr.write(self.style.ERROR("Backup command hanya untuk MySQL production."))
            return

        out_dir = Path(options["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        outfile = out_dir / f"hris_{db['NAME']}_{stamp}.sql.gz"

        cmd = [
            "mysqldump",
            f"--host={db.get('HOST') or 'localhost'}",
            f"--port={db.get('PORT') or '3306'}",
            f"--user={db['USER']}",
            f"--password={db['PASSWORD']}",
            "--single-transaction",
            "--routines",
            "--triggers",
            db["NAME"],
        ]
        with open(outfile, "wb") as handle:
            dump = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            gzip = subprocess.Popen(["gzip"], stdin=dump.stdout, stdout=handle)
            dump.stdout.close()
            gzip.communicate()
            stderr = dump.stderr.read().decode() if dump.stderr else ""
            rc = dump.wait()
            if rc != 0:
                outfile.unlink(missing_ok=True)
                raise RuntimeError(f"mysqldump gagal: {stderr}")

        self.stdout.write(self.style.SUCCESS(f"Backup tersimpan: {outfile}"))
