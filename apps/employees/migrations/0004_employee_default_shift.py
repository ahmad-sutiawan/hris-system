import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0003_alter_employee_allowance_meal_and_more"),
        ("shifts", "0003_delete_dayswaprequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="default_shift",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="default_for_employees",
                to="shifts.shift",
                verbose_name="Shift default",
            ),
        ),
    ]
