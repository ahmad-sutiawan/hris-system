from django.utils import timezone

from apps.core.models import Notification


def leave_request_link(leave_request) -> str:
    from django.conf import settings

    return f"{settings.HRIS_SITE_URL}/leave/?req={leave_request.pk}"


def overtime_request_link(overtime_request) -> str:
    from django.conf import settings

    return f"{settings.HRIS_SITE_URL}/overtime/?req={overtime_request.pk}"


def dismiss_request_notifications(*, link_fragment: str, category=None) -> int:
    """Mark unread notifications matching a request link as read."""
    qs = Notification.objects.filter(is_read=False, link__contains=link_fragment)
    if category is not None:
        qs = qs.filter(category=category)
    return qs.update(is_read=True, read_at=timezone.now())


def dismiss_leave_request_notifications(leave_request) -> int:
    return dismiss_request_notifications(
        link_fragment=f"req={leave_request.pk}",
        category=Notification.Category.LEAVE,
    )


def dismiss_overtime_request_notifications(overtime_request) -> int:
    return dismiss_request_notifications(
        link_fragment=f"req={overtime_request.pk}",
        category=Notification.Category.ATTENDANCE,
    )
