from django.urls import reverse

from apps.core.decorators import user_has_admin_console
from apps.core.models import Notification
from apps.web.admin_crud.registry import ensure_bootstrapped, resources_by_app


def notifications(request):
    if not request.user.is_authenticated:
        return {"unread_notifications": 0, "recent_notifications": []}
    qs = Notification.objects.filter(user=request.user, is_read=False)
    return {
        "unread_notifications": qs.count(),
        "recent_notifications": Notification.objects.filter(user=request.user).order_by(
            "-created_at"
        )[:5],
    }


def admin_navigation(request):
    if not user_has_admin_console(request.user):
        return {"show_admin_nav": False, "admin_nav_apps": []}

    ensure_bootstrapped()
    apps = []
    for section, resources in resources_by_app():
        items = []
        for resource in resources:
            items.append(
                {
                    "slug": resource.slug,
                    "label": resource.title_plural,
                    "url": reverse("web:manage_list", kwargs={"slug": resource.slug}),
                }
            )
        apps.append({"section": section, "items": items})

    return {
        "show_admin_nav": True,
        "admin_nav_apps": apps,
    }
