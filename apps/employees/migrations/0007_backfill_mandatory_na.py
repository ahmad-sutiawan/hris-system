from django.db import migrations


def backfill_mandatory(apps, schema_editor):
    Employee = apps.get_model("employees", "Employee")
    Department = apps.get_model("organization", "Department")
    JobPosition = apps.get_model("organization", "JobPosition")
    JobLevel = apps.get_model("organization", "JobLevel")
    User = apps.get_model("core", "User")

    NA = "N/A"
    text_fields = (
        "nik",
        "email",
        "phone",
        "address",
        "mother_name",
        "birth_place",
        "tax_status",
        "npwp",
        "bank_name",
        "bank_account_number",
        "bank_account_name",
        "bpjs_kesehatan_number",
        "bpjs_ketenagakerjaan_number",
    )

    for employee in Employee.objects.all().iterator():
        changed = False
        for field in text_fields:
            if not (getattr(employee, field) or "").strip():
                setattr(employee, field, NA)
                changed = True
        if not employee.gender:
            employee.gender = "na"
            changed = True
        if not employee.marital_status:
            employee.marital_status = "na"
            changed = True
        if not employee.join_date:
            employee.join_date = employee.created_at.date() if employee.created_at else None
            if employee.join_date:
                changed = True
        if employee.plant_id:
            if not employee.department_id:
                dept = Department.objects.filter(
                    tenant_id=employee.tenant_id,
                    plant_id=employee.plant_id,
                    is_active=True,
                ).first()
                if dept:
                    employee.department_id = dept.pk
                    changed = True
            if not employee.job_position_id:
                job = JobPosition.objects.filter(
                    tenant_id=employee.tenant_id,
                    plant_id=employee.plant_id,
                    is_active=True,
                ).first()
                if job:
                    employee.job_position_id = job.pk
                    changed = True
            if not employee.job_level_id:
                level = JobLevel.objects.filter(tenant_id=employee.tenant_id).order_by("rank").first()
                if level:
                    employee.job_level_id = level.pk
                    changed = True
            if not employee.manager_id:
                manager = (
                    Employee.objects.filter(
                        tenant_id=employee.tenant_id,
                        plant_id=employee.plant_id,
                        user__role="manager",
                    )
                    .exclude(pk=employee.pk)
                    .first()
                )
                if not manager:
                    manager = (
                        Employee.objects.filter(
                            tenant_id=employee.tenant_id,
                            plant_id=employee.plant_id,
                        )
                        .exclude(pk=employee.pk)
                        .first()
                    )
                if manager:
                    employee.manager_id = manager.pk
                    changed = True
        if changed:
            employee.save()


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0006_alignment_hris_tahap1"),
        ("organization", "0004_alignment_hris_tahap1"),
    ]

    operations = [
        migrations.RunPython(backfill_mandatory, migrations.RunPython.noop),
    ]
