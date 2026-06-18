from django.db import migrations


def enable_cross_day_for_night_shifts(apps, schema_editor):
    Shift = apps.get_model("shifts", "Shift")
    for shift in Shift.objects.all().iterator():
        if (
            shift.scheduled_check_in
            and shift.scheduled_check_out
            and shift.scheduled_check_out <= shift.scheduled_check_in
            and not shift.cross_day
        ):
            shift.cross_day = True
            shift.save(update_fields=["cross_day"])


class Migration(migrations.Migration):
    dependencies = [
        ("shifts", "0003_delete_dayswaprequest"),
    ]

    operations = [
        migrations.RunPython(enable_cross_day_for_night_shifts, migrations.RunPython.noop),
    ]
