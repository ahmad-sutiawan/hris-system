from django.db import migrations, models
import django.db.models.deletion


def backfill_attendance_punches(apps, schema_editor):
    AttendanceRecord = apps.get_model("attendance", "AttendanceRecord")
    AttendancePunch = apps.get_model("attendance", "AttendancePunch")

    for record in AttendanceRecord.objects.iterator():
        if record.check_in:
            AttendancePunch.objects.create(
                tenant_id=record.tenant_id,
                attendance_record_id=record.pk,
                employee_id=record.employee_id,
                work_date=record.work_date,
                punch_type="in",
                punched_at=record.check_in,
                source=record.source,
                photo=record.check_in_photo,
                latitude=record.latitude,
                longitude=record.longitude,
                notes=record.notes,
            )
        if record.check_out:
            AttendancePunch.objects.create(
                tenant_id=record.tenant_id,
                attendance_record_id=record.pk,
                employee_id=record.employee_id,
                work_date=record.work_date,
                punch_type="out",
                punched_at=record.check_out,
                source=record.source,
                photo=record.check_out_photo,
                latitude=record.latitude,
                longitude=record.longitude,
                notes=record.notes,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("attendance", "0011_plant_fk_set_null_on_delete"),
        ("employees", "0012_employee_nik_lookup"),
    ]

    operations = [
        migrations.CreateModel(
            name="AttendancePunch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("work_date", models.DateField(db_index=True)),
                (
                    "punch_type",
                    models.CharField(
                        choices=[("in", "Clock In"), ("out", "Clock Out")],
                        max_length=8,
                    ),
                ),
                ("punched_at", models.DateTimeField(db_index=True)),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("web", "Web"),
                            ("mobile", "Mobile"),
                            ("kiosk", "Kiosk"),
                            ("import", "Import"),
                            ("manual", "Manual"),
                        ],
                        default="web",
                        max_length=20,
                    ),
                ),
                ("photo", models.ImageField(blank=True, null=True, upload_to="attendance/%Y/%m/")),
                ("latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("notes", models.TextField(blank=True)),
                (
                    "attendance_record",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="punches",
                        to="attendance.attendancerecord",
                    ),
                ),
                (
                    "employee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attendance_punches",
                        to="employees.employee",
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_set",
                        to="core.tenant",
                    ),
                ),
            ],
            options={
                "ordering": ["punched_at", "pk"],
            },
        ),
        migrations.AddIndex(
            model_name="attendancepunch",
            index=models.Index(fields=["tenant", "employee", "work_date"], name="attendance__tenant__8f0a2d_idx"),
        ),
        migrations.AddIndex(
            model_name="attendancepunch",
            index=models.Index(fields=["attendance_record", "punched_at"], name="attendance__attenda_5c2f1a_idx"),
        ),
        migrations.RunPython(backfill_attendance_punches, migrations.RunPython.noop),
    ]
