from django.db import migrations, models


def backfill_status_employee(apps, schema_editor):
    Employee = apps.get_model("employees", "Employee")
    for emp in Employee.objects.all().iterator():
        if emp.status_employee:
            continue
        if emp.status == "resigned":
            emp.status_employee = "Resigned"
        elif emp.status == "contract":
            emp.status_employee = "Contract"
        elif emp.status == "permanent" and emp.salary_scheme == "daily":
            emp.status_employee = "Harian"
        elif emp.status == "permanent":
            emp.status_employee = "Permanent"
        else:
            emp.status_employee = ""
        emp.save(update_fields=["status_employee"])


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0008_p0_production_hardening"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="status_employee",
            field=models.CharField(
                blank=True,
                help_text="Status Employee dari export Talenta (Harian, Contract, Permanent).",
                max_length=32,
            ),
        ),
        migrations.RunPython(backfill_status_employee, migrations.RunPython.noop),
    ]
