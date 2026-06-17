from decimal import Decimal

from apps.payroll.data.ter_pp58 import TER_BRACKETS_BY_CATEGORY, TER_PTKP_BY_CATEGORY
from apps.payroll.models import Pph21TerBracket, Pph21TerCategory, Pph21TerPtkpMapping

CATEGORY_NAMES = {
    "A": "TER A (TK/0, TK/1, K/0)",
    "B": "TER B (TK/2, TK/3, K/1, K/2)",
    "C": "TER C (K/3)",
}


def seed_ter_master(tenant) -> None:
    """Populate TER categories, PTKP mappings, and brackets for a tenant."""
    for code, ptkp_list in TER_PTKP_BY_CATEGORY.items():
        category, _ = Pph21TerCategory.objects.update_or_create(
            tenant=tenant,
            code=code,
            defaults={
                "name": CATEGORY_NAMES[code],
                "description": "PP No. 58 Tahun 2023 — Tarif Efektif Bulanan",
                "is_active": True,
            },
        )
        for ptkp_code in ptkp_list:
            Pph21TerPtkpMapping.objects.update_or_create(
                tenant=tenant,
                ptkp_code=ptkp_code,
                defaults={"category": category},
            )
        Pph21TerBracket.objects.filter(tenant=tenant, category=category).delete()
        for idx, (income_from, income_to, rate) in enumerate(
            TER_BRACKETS_BY_CATEGORY[code], start=1
        ):
            Pph21TerBracket.objects.create(
                tenant=tenant,
                category=category,
                bracket_no=idx,
                income_from=income_from,
                income_to=income_to,
                rate=rate,
            )


def ter_category_for_ptkp(tenant, ptkp_code: str) -> str | None:
    if not ptkp_code:
        return None
    mapping = (
        Pph21TerPtkpMapping.objects.filter(tenant=tenant, ptkp_code=ptkp_code.strip())
        .select_related("category")
        .first()
    )
    return mapping.category.code if mapping else None


def lookup_ter_rate(*, tenant, gross: Decimal, ptkp_code: str) -> Decimal:
    """Return effective monthly TER rate for gross income and PTKP status."""
    if gross <= 0 or not ptkp_code:
        return Decimal("0")

    category_code = ter_category_for_ptkp(tenant, ptkp_code)
    if not category_code:
        return Decimal("0")

    brackets = Pph21TerBracket.objects.filter(
        tenant=tenant,
        category__code=category_code,
        category__is_active=True,
    ).order_by("bracket_no")

    if not brackets.exists():
        for income_from, income_to, rate in TER_BRACKETS_BY_CATEGORY.get(category_code, ()):
            if income_to is None:
                if gross > income_from:
                    return rate
                continue
            if gross <= income_to:
                if income_from == 0 or gross > income_from:
                    return rate
        return Decimal("0.34")

    for bracket in brackets:
        if bracket.income_to is None:
            if gross > bracket.income_from:
                return bracket.rate
            continue
        if gross <= bracket.income_to:
            if bracket.income_from == 0 or gross > bracket.income_from:
                return bracket.rate
    return Decimal("0.34")


def preview_pph21(*, tenant, gross: Decimal, ptkp_code: str) -> dict:
    rate = lookup_ter_rate(tenant=tenant, gross=gross, ptkp_code=ptkp_code)
    tax = (gross * rate).quantize(Decimal("0.01")) if gross > 0 else Decimal("0")
    category = ter_category_for_ptkp(tenant, ptkp_code)
    return {
        "ptkp_code": ptkp_code or "",
        "ter_category": category,
        "ter_rate_percent": (rate * Decimal("100")).quantize(Decimal("0.0001")),
        "gross_monthly": gross,
        "pph21_monthly": tax,
    }
