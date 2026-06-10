from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from apps.core.models import Notification


def create_notification(*, tenant, user, category, title, message, link=""):
    if not user:
        return None
    return Notification.objects.create(
        tenant=tenant,
        user=user,
        category=category,
        title=title,
        message=message,
        link=link,
    )


def send_email_notification(*, to_email, subject, message):
    if not to_email:
        return False
    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@hris.local"),
        recipient_list=[to_email],
        fail_silently=True,
    )
    return True


def notify_user(*, tenant, user, category, title, message, link="", send_email=True):
    create_notification(
        tenant=tenant,
        user=user,
        category=category,
        title=title,
        message=message,
        link=link,
    )
    if send_email and user.email:
        send_email_notification(
            to_email=user.email,
            subject=f"[HRIS-Lite] {title}",
            message=message,
        )


def mark_notifications_read(user, notification_ids=None):
    qs = Notification.objects.filter(user=user, is_read=False)
    if notification_ids:
        qs = qs.filter(pk__in=notification_ids)
    qs.update(is_read=True, read_at=timezone.now())
