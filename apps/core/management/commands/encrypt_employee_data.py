from django.core.management.base import BaseCommand

from apps.core.encryption import ENC_PREFIX
from apps.employees.models import Employee


SENSITIVE_FIELDS = (
    "nik",
    "npwp",
    "bank_account_number",
    "bank_account_name",
    "bpjs_kesehatan_number",
    "bpjs_ketenagakerjaan_number",
    "base_salary",
    "allowance_transport",
    "allowance_meal",
    "allowance_position",
)


class Command(BaseCommand):
    help = "Enkripsi data karyawan yang masih plaintext di database."

    def handle(self, *args, **options):
        updated = 0
        for employee in Employee.objects.iterator(chunk_size=100):
            raw = (
                Employee.objects.filter(pk=employee.pk)
                .values(*SENSITIVE_FIELDS)
                .first()
            )
            if not raw:
                continue
            if all(
                not raw[f] or str(raw[f]).startswith(ENC_PREFIX) for f in SENSITIVE_FIELDS
            ):
                continue
            employee.save(update_fields=list(SENSITIVE_FIELDS))
            updated += 1
        self.stdout.write(self.style.SUCCESS(f"Enkripsi selesai: {updated} karyawan diperbarui."))
