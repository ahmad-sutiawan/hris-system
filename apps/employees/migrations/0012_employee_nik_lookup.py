import hashlib

from django.db import migrations, models


def _plain_nik(stored: str) -> str:
    if not stored:
        return ""
    if str(stored).startswith("enc:v1:"):
        from apps.core.encryption import decrypt_value

        return decrypt_value(str(stored))
    return str(stored).strip()


def backfill_nik_lookup(apps, schema_editor):
    Employee = apps.get_model("employees", "Employee")
    batch = []
    for employee in Employee.objects.exclude(nik="").iterator(chunk_size=500):
        plain = _plain_nik(employee.nik)
        lookup = hashlib.sha256(plain.encode("utf-8")).hexdigest() if plain else ""
        if lookup and employee.nik_lookup != lookup:
            employee.nik_lookup = lookup
            batch.append(employee)
        if len(batch) >= 500:
            Employee.objects.bulk_update(batch, ["nik_lookup"])
            batch.clear()
    if batch:
        Employee.objects.bulk_update(batch, ["nik_lookup"])


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0011_talenta_field_lengths"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="nik_lookup",
            field=models.CharField(
                blank=True,
                db_index=True,
                editable=False,
                help_text="SHA-256 hash NIK untuk login (bukan data sensitif).",
                max_length=64,
            ),
        ),
        migrations.RunPython(backfill_nik_lookup, migrations.RunPython.noop),
    ]
