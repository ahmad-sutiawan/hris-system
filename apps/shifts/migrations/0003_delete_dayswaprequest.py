from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("shifts", "0002_dayswaprequest"),
    ]

    operations = [
        migrations.DeleteModel(
            name="DaySwapRequest",
        ),
    ]
