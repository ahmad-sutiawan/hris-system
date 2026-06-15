from django.utils.text import slugify

from apps.organization.models import Department


def department_code_from_name(
    name: str,
    *,
    tenant_id,
    plant_id,
    exclude_pk=None,
) -> str:
    base = slugify(name).upper().replace("-", "_")[:32] or "DEPT"
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
