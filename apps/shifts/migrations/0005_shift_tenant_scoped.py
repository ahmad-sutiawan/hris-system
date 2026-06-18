from django.db import migrations, models
import django.db.models.deletion


def clear_shift_plant_and_dedupe(apps, schema_editor):
    Shift = apps.get_model("shifts", "Shift")
    ShiftAssignment = apps.get_model("shifts", "ShiftAssignment")
    Plant = apps.get_model("core", "Plant")

    kept_by_code: dict[tuple[int, str], int] = {}
    for shift in Shift.objects.order_by("id"):
        key = (shift.tenant_id, shift.code)
        if key in kept_by_code:
            keeper_id = kept_by_code[key]
            ShiftAssignment.objects.filter(shift_id=shift.id).update(shift_id=keeper_id)
            Plant.objects.filter(default_shift_id=shift.id).update(default_shift_id=keeper_id)
            shift.delete()
            continue
        kept_by_code[key] = shift.id
        if shift.plant_id is not None:
            shift.plant_id = None
            shift.save(update_fields=["plant_id"])


def _mysql_indexes(cursor, table):
    cursor.execute(f"SHOW INDEX FROM `{table}`")
    by_key = {}
    for row in cursor.fetchall():
        key_name = row[2]
        by_key.setdefault(key_name, {"non_unique": row[1], "cols": {}})
        by_key[key_name]["cols"][row[3]] = row[4]
    return {
        name: {
            "non_unique": meta["non_unique"],
            "columns": [meta["cols"][i] for i in sorted(meta["cols"])],
        }
        for name, meta in by_key.items()
    }


def apply_shift_tenant_code_unique(apps, schema_editor):
    """MySQL-safe unique_together swap; avoids duplicate tenant_id index errors."""
    connection = schema_editor.connection
    Shift = apps.get_model("shifts", "Shift")

    if connection.vendor != "mysql":
        schema_editor.alter_unique_together(
            Shift,
            [("tenant", "plant", "code")],
            [("tenant", "code")],
        )
        return

    table = Shift._meta.db_table
    old_cols = ("tenant_id", "plant_id", "code")
    new_cols = ("tenant_id", "code")
    new_index = "shifts_shift_tenant_code_uniq"

    with connection.cursor() as cursor:
        indexes = _mysql_indexes(cursor, table)
        for name, meta in indexes.items():
            if meta["non_unique"] == 0 and tuple(meta["columns"]) == old_cols:
                cursor.execute(f"ALTER TABLE `{table}` DROP INDEX `{name}`")

        indexes = _mysql_indexes(cursor, table)
        has_new = any(
            meta["non_unique"] == 0 and tuple(meta["columns"]) == new_cols
            for meta in indexes.values()
        )
        if not has_new:
            cursor.execute(
                f"ALTER TABLE `{table}` ADD UNIQUE INDEX `{new_index}` "
                f"(`tenant_id`, `code`)"
            )


class Migration(migrations.Migration):
    dependencies = [
        ("shifts", "0004_enable_cross_day_night_shifts"),
    ]

    operations = [
        migrations.AlterField(
            model_name="shift",
            name="plant",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional. Shifts are shared at tenant level; plant link is legacy only.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="shifts",
                to="core.plant",
            ),
        ),
        migrations.RunPython(clear_shift_plant_and_dedupe, migrations.RunPython.noop),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterUniqueTogether(
                    name="shift",
                    unique_together={("tenant", "code")},
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    apply_shift_tenant_code_unique,
                    migrations.RunPython.noop,
                ),
            ],
        ),
    ]
