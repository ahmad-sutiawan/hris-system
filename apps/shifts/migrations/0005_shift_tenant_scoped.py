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
        migrations.AlterUniqueTogether(
            name="shift",
            unique_together={("tenant", "code")},
        ),
    ]
