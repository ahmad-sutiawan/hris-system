"""
Bersihkan database dev agar selaras dengan data yang tampil di Admin Console.

Menghapus:
- artefak seed_demo (karyawan/user PLT01-*)
- master data demo yang tidak ada di UI (LegalEntity demo)
- sesi Django & token blacklist (bukan data bisnis)
- database test_bps_hris (isolasi test Django)

Jalankan ANALYZE TABLE agar statistik ServBay/phpMyAdmin akurat.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from apps.employees.models import Employee
from apps.organization.models import LegalEntity

User = get_user_model()

DEMO_EMPLOYEE_PREFIXES = ("PLT01-",)
DEMO_LEGAL_ENTITY_NAMES = ("PT Demo Manufaktur",)


class Command(BaseCommand):
    help = "Bersihkan artefak non-UI dari bps_hris dan sinkronkan statistik MySQL."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-backup",
            action="store_true",
            help="Lewati backup otomatis sebelum pembersihan.",
        )
        parser.add_argument(
            "--keep-demo-employees",
            action="store_true",
            help="Jangan hapus karyawan demo PLT01 (seed_demo).",
        )
        parser.add_argument(
            "--drop-test-db",
            action="store_true",
            default=True,
            help="Hapus database test_bps_hris (default: aktif).",
        )
        parser.add_argument(
            "--no-drop-test-db",
            action="store_false",
            dest="drop_test_db",
            help="Biarkan database test_bps_hris.",
        )

    def handle(self, *args, **options):
        if not options["skip_backup"]:
            self.stdout.write("Membuat backup...")
            call_command("backup_database")

        stats = {
            "demo_users": 0,
            "demo_employees": 0,
            "demo_legal_entities": 0,
            "sessions": 0,
            "tokens": 0,
        }

        with transaction.atomic():
            if not options["keep_demo_employees"]:
                demo_employees = Employee.objects.filter(
                    employee_id__startswith=DEMO_EMPLOYEE_PREFIXES[0]
                )
                demo_user_ids = list(
                    demo_employees.exclude(user_id__isnull=True).values_list("user_id", flat=True)
                )
                stats["demo_employees"] = demo_employees.count()
                demo_employees.delete()
                if demo_user_ids:
                    stats["demo_users"] = User.objects.filter(pk__in=demo_user_ids).delete()[0]

            demo_entities = LegalEntity.objects.filter(name__in=DEMO_LEGAL_ENTITY_NAMES)
            stats["demo_legal_entities"] = demo_entities.count()
            demo_entities.delete()

            stats["sessions"] = Session.objects.count()
            Session.objects.all().delete()

            stats["tokens"] = self._clear_token_blacklist()

        self._analyze_tables()

        if options["drop_test_db"]:
            self._drop_test_database()

        self.stdout.write(self.style.SUCCESS("Pembersihan selesai:"))
        for key, value in stats.items():
            self.stdout.write(f"  {key}: {value}")

    def _clear_token_blacklist(self) -> int:
        try:
            from rest_framework_simplejwt.token_blacklist.models import (
                BlacklistedToken,
                OutstandingToken,
            )
        except ImportError:
            return 0

        blacklisted = BlacklistedToken.objects.count()
        outstanding = OutstandingToken.objects.count()
        BlacklistedToken.objects.all().delete()
        OutstandingToken.objects.all().delete()
        return blacklisted + outstanding

    def _analyze_tables(self):
        db_name = settings.DATABASES["default"]["NAME"]
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s AND table_type = 'BASE TABLE'
                """,
                [db_name],
            )
            tables = [row[0] for row in cursor.fetchall()]

        self.stdout.write(f"ANALYZE TABLE pada {len(tables)} tabel...")
        with connection.cursor() as cursor:
            for table in tables:
                cursor.execute(f"ANALYZE TABLE `{table}`")

    def _drop_test_database(self):
        db_name = settings.DATABASES["default"]["NAME"]
        test_db = f"test_{db_name}"
        if test_db == db_name:
            return
        with connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{test_db}`")
        self.stdout.write(self.style.WARNING(f"Database {test_db} dihapus."))
