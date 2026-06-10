from django import template
from django.utils.safestring import mark_safe

register = template.Library()

STATUS_BADGE_MAP = {
    "pending": "pending",
    "draft": "draft",
    "probation": "probation",
    "approved": "approved",
    "finalized": "finalized",
    "permanent": "permanent",
    "paid": "paid",
    "rejected": "rejected",
    "resigned": "resigned",
    "inactive": "inactive",
    "unpaid": "unpaid",
    "review": "review",
    "contract": "contract",
    "calculated": "review",
    "create": "approved",
    "update": "review",
    "delete": "rejected",
    "access": "default",
}


@register.simple_tag
def status_badge(status, label=None):
    css = STATUS_BADGE_MAP.get(str(status).lower(), "default")
    text = label if label is not None else str(status).replace("_", " ").title()
    return mark_safe(f'<span class="hris-badge hris-badge--{css}">{text}</span>')


@register.filter
def initials(value):
    if not value:
        return "?"
    parts = str(value).strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return parts[0][:2].upper()
