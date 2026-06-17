import re

from django.utils.text import slugify

from apps.organization.models import Department, JobLevel, JobPosition


def _base_code(name: str, *, fallback: str = "ITEM") -> str:
    normalized = re.sub(r"\s+", " ", (name or "").strip())
    base = slugify(normalized).upper().replace("-", "_")[:32]
    return base or fallback


def _unique_code(model, filters, base: str) -> str:
    code = base
    suffix = 1
    while model.objects.filter(**filters, code=code).exists():
        suffix += 1
        code = f"{base[:28]}_{suffix}"[:32]
    return code


def department_code_from_name(
    name: str,
    *,
    tenant_id,
    plant_id,
    exclude_pk=None,
) -> str:
    base = _base_code(name, fallback="DEPT")
    code = base
    suffix = 1
    while True:
        qs = Department.objects.filter(tenant_id=tenant_id, plant_id=plant_id, code=code)
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        if not qs.exists():
            return code
        suffix += 1
        code = f"{base[:28]}_{suffix}"[:32]


def job_position_code_from_name(name: str, *, tenant_id, plant_id) -> str:
    base = _base_code(name, fallback="JOB")
    return _unique_code(
        JobPosition,
        {"tenant_id": tenant_id, "plant_id": plant_id},
        base,
    )


def job_level_code_from_name(name: str, *, tenant_id) -> str:
    base = _base_code(name, fallback="LEVEL")
    return _unique_code(JobLevel, {"tenant_id": tenant_id}, base)
