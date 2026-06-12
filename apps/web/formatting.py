"""Indonesian number display helpers for UI and admin tables."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

MONEY_FIELD_HINTS = (
    "amount",
    "wage",
    "salary",
    "allowance",
    "deduction",
    "gross",
    "net",
    "price",
    "cost",
    "compensation",
)


def _to_decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _format_int_part(value: int) -> str:
    negative = value < 0
    absolute = abs(value)
    if absolute < 1000:
        text = str(absolute)
    else:
        text = f"{absolute:,}".replace(",", ".")
    return f"-{text}" if negative else text


def format_number(
    value,
    *,
    prefix: str = "",
    max_decimals: int = 2,
    money: bool = False,
) -> str:
    """
    Format numbers for Indonesian UI:
    - Thousand separator: dot (.)
    - Decimal separator: comma (,)
    - Trailing zeros removed (no forced .00)
    """
    decimal_value = _to_decimal(value)
    if decimal_value is None:
        return "—" if value is None or value == "" else str(value)

    if money:
        decimal_value = decimal_value.quantize(Decimal("1"))
        max_decimals = 0
        prefix = "Rp "

    negative = decimal_value < 0
    decimal_value = abs(decimal_value)

    if max_decimals <= 0:
        int_part = int(decimal_value.quantize(Decimal("1")))
        frac_digits = ""
    else:
        quant = Decimal("1").scaleb(-max_decimals)
        decimal_value = decimal_value.quantize(quant)
        int_part = int(decimal_value)
        remainder = decimal_value - Decimal(int_part)
        if remainder == 0:
            frac_digits = ""
        else:
            frac_digits = f"{remainder:.{max_decimals}f}".split(".")[1].rstrip("0")

    body = _format_int_part(-int_part if negative else int_part)
    if frac_digits:
        body = f"{body},{frac_digits}"

    return f"{prefix}{body}"


def format_rupiah(value) -> str:
    return format_number(value, money=True)


def is_money_field(attr_path: str) -> bool:
    lower = attr_path.lower()
    return any(hint in lower for hint in MONEY_FIELD_HINTS)


def format_cell_value(value, attr_path: str = "") -> str:
    if value is None:
        return "-"
    if hasattr(value, "all"):
        return str(value)
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M") if hasattr(value, "hour") else value.strftime("%Y-%m-%d")
    if isinstance(value, bool):
        return "Ya" if value else "Tidak"
    if isinstance(value, (Decimal, int, float)) and not isinstance(value, bool):
        if is_money_field(attr_path):
            return format_rupiah(value)
        if isinstance(value, int):
            return format_number(value, max_decimals=0)
        return format_number(value, max_decimals=2)
    return value
