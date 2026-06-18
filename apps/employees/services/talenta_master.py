"""Auto-provision Talenta master values saat import."""

from __future__ import annotations

from django.utils.text import slugify

from apps.employees.models import TalentaMaster
from apps.employees.talenta_mapping import TALENTA_MASTER_COLUMN_MAP


def get_or_create_talenta_master(
    tenant,
    *,
    category: str,
    name: str,
    cache: dict[tuple[str, str], TalentaMaster] | None = None,
) -> TalentaMaster | None:
    name = " ".join((name or "").split())
    if not name:
        return None
    key = (category, name.lower())
    if cache is not None and key in cache:
        return cache[key]

    code = slugify(name).upper().replace("-", "_")[:60] or "ITEM"
    obj, _ = TalentaMaster.objects.get_or_create(
        tenant=tenant,
        category=category,
        name=name,
        defaults={"code": code},
    )
    if cache is not None:
        cache[key] = obj
    return obj


def resolve_talenta_masters_from_row(tenant, row, cache: dict | None = None) -> dict:
    import re

    def cell(key: str) -> str:
        if key not in row:
            return ""
        return re.sub(r"\s+", " ", str(row[key] or "").strip())

    resolved: dict = {}
    for column, category in TALENTA_MASTER_COLUMN_MAP.items():
        value = cell(column)
        resolved[category] = get_or_create_talenta_master(
            tenant, category=category, name=value, cache=cache
        )
    return resolved
