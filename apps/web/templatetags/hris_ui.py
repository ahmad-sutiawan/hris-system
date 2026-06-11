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
    "cancelled": "default",
}


@register.simple_tag
def status_badge(status, label=None):
    css = STATUS_BADGE_MAP.get(str(status).lower(), "default")
    text = label if label is not None else str(status).replace("_", " ").title()
    return mark_safe(f'<span class="hris-badge hris-badge--{css}">{text}</span>')


@register.simple_tag(takes_context=True)
def nav_is_active(context, *url_names):
    request = context.get("request")
    if not request or not getattr(request, "resolver_match", None):
        return ""
    if request.resolver_match.url_name in url_names:
        return " is-active"
    return ""


@register.simple_tag(takes_context=True)
def nav_master_active(context, slug):
    request = context.get("request")
    if not request or not getattr(request, "resolver_match", None):
        return ""
    match = request.resolver_match
    if match.kwargs.get("slug") == slug and match.url_name in {
        "master_list",
        "master_create",
        "master_edit",
    }:
        return " is-active"
    return ""


@register.filter
def initials(value):
    if not value:
        return "?"
    parts = str(value).strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return parts[0][:2].upper()


@register.filter
def local_datetime(value, arg=None):
    if not value:
        return "-"
    from django.utils import timezone
    from django.utils.formats import date_format

    if timezone.is_aware(value):
        value = timezone.localtime(value)
    fmt = arg or "d M Y H:i"
    return date_format(value, fmt, use_l10n=False)


@register.filter
def local_date(value, arg=None):
    if not value:
        return "-"
    from django.utils import timezone
    from django.utils.formats import date_format

    if hasattr(value, "hour"):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        fmt = arg or "d M Y"
        return date_format(value, fmt, use_l10n=False)
    fmt = arg or "d M Y"
    return date_format(value, fmt, use_l10n=False)
