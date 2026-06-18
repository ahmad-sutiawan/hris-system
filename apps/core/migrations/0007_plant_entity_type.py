from django.db import migrations, models
import django.db.models.deletion
from django.utils.text import slugify


def _parent_pt_name(branch_name: str) -> str:
    name = (branch_name or "").strip()
    for suffix in (" (Harian)", " (SPV Up)", " (Staff)"):
        if name.endswith(suffix):
            return name[: -len(suffix)].strip()
    return name or "Plant Utama"


def backfill_pt_parents(apps, schema_editor):
    Plant = apps.get_model("core", "Plant")
    pt_cache: dict[tuple[int, str], int] = {}
    for branch in Plant.objects.filter(entity_type="branch").order_by("id"):
        pt_name = _parent_pt_name(branch.name)
        key = (branch.tenant_id, pt_name)
        if key not in pt_cache:
            code = slugify(pt_name).upper().replace("-", "_")[:20] or "PT"
            plant, _ = Plant.objects.get_or_create(
                tenant_id=branch.tenant_id,
                code=code,
                defaults={
                    "name": pt_name,
                    "entity_type": "pt",
                    "is_active": True,
                },
            )
            if plant.entity_type != "pt":
                plant.entity_type = "pt"
                plant.save(update_fields=["entity_type"])
            pt_cache[key] = plant.id
        if branch.parent_id != pt_cache[key]:
            branch.parent_id = pt_cache[key]
            branch.save(update_fields=["parent_id"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_alignment_hris_tahap1"),
    ]

    operations = [
        migrations.AddField(
            model_name="plant",
            name="entity_type",
            field=models.CharField(
                choices=[("pt", "Plant (PT)"), ("branch", "Branch")],
                default="branch",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="plant",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                help_text="PT induk untuk cabang karyawan (BPS Harian, Staff, SPV Up).",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="child_branches",
                to="core.plant",
            ),
        ),
        migrations.RunPython(backfill_pt_parents, migrations.RunPython.noop),
    ]
