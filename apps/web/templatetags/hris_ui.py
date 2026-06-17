from django import template
from django.utils.safestring import mark_safe

from apps.core.approval import can_approve_employee, can_approve_request
from apps.web.formatting import format_number, format_rupiah
from apps.web.nav_icons import resolve_nav_icon

register = template.Library()

STATUS_BADGE_MAP = {
    "pending": "pending",
    "pending_approval": "review",
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
def can_approve_employee_tag(approver, employee):
    return can_approve_employee(approver, employee)


@register.simple_tag
def can_approve_request_tag(approver, employee, request_type, approval_step=1):
    return can_approve_request(approver, employee, request_type, approval_step)


@register.simple_tag
def nav_icon(key):
    inner = resolve_nav_icon(key)
    return mark_safe(
        f'<svg fill="none" viewBox="0 0 24 24" stroke="currentColor" '
        f'stroke-width="1.75" aria-hidden="true">{inner}</svg>'
    )


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
def rupiah(value):
    return format_rupiah(value)


@register.filter
def num(value, decimals="2"):
    try:
        max_decimals = int(decimals)
    except (TypeError, ValueError):
        max_decimals = 2
    return format_number(value, max_decimals=max(0, max_decimals))


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
