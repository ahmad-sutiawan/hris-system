from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("attendance", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="attendancerecord",
            name="check_in_photo",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="attendance/%Y/%m/",
                verbose_name="Foto clock in",
            ),
        ),
        migrations.AddField(
            model_name="attendancerecord",
            name="check_out_photo",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="attendance/%Y/%m/",
                verbose_name="Foto clock out",
            ),
        ),
    ]
