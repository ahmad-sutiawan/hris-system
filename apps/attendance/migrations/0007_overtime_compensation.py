from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0006_overtime_request_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="overtimerequest",
            name="compensation_mode",
            field=models.CharField(
                choices=[("cash", "Diuangkan"), ("leave", "Tambah Jatah Cuti")],
                default="cash",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="overtimerequest",
            name="leave_days_credited",
            field=models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=6),
        ),
    ]
