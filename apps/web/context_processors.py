from django.urls import reverse

from apps.core.decorators import (
    user_can_manage_employees,
    user_can_manage_master_data,
    user_has_admin_console,
)
from apps.core.models import Notification
from apps.core.services.announcements import active_announcements_for_user
from apps.web.admin_crud.registry import (
    ensure_bootstrapped,
    master_nav_items,
    resources_by_app,
)


def announcement_banners(request):
    if not request.user.is_authenticated:
        return {"announcement_banners": [], "active_announcement_count": 0}
    banners = active_announcements_for_user(request.user, limit=5)
    return {
        "announcement_banners": banners,
        "active_announcement_count": len(banners),
    }


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
    for section, resources in resources_by_app(exclude_master=True):
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


def employee_navigation(request):
    return {
        "show_employee_nav": user_can_manage_employees(request.user),
    }


def master_data_navigation(request):
    if not user_can_manage_master_data(request.user):
        return {"show_master_nav": False, "master_nav_items": []}

    ensure_bootstrapped()
    items = []
    for resource in master_nav_items():
        items.append(
            {
                "slug": resource.slug,
                "label": resource.title_plural,
                "url": reverse("web:master_list", kwargs={"slug": resource.slug}),
            }
        )

    return {
        "show_master_nav": True,
        "master_nav_items": items,
    }
