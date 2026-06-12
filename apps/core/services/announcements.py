from __future__ import annotations

from django.db.models import Case, IntegerField, Q, When
from django.utils import timezone

from apps.core.models import Announcement, AnnouncementDismissal, User


def _base_announcement_queryset(*, tenant, now=None):
    now = now or timezone.now()
    return Announcement.objects.filter(
        tenant=tenant,
        is_active=True,
        publish_start__lte=now,
    ).filter(Q(publish_end__isnull=True) | Q(publish_end__gte=now))


def _plant_filter(qs, user: User):
    if user.plant_id:
        qs = qs.filter(Q(plant__isnull=True) | Q(plant_id=user.plant_id))
    return qs


def _matches_user_role(announcement: Announcement, user: User) -> bool:
    roles = announcement.target_roles or []
    return not roles or user.role in roles


def dismissed_announcement_ids(user: User) -> set[int]:
    if not user.is_authenticated:
        return set()
    return set(
        AnnouncementDismissal.objects.filter(user=user).values_list(
            "announcement_id",
            flat=True,
        )
    )


def _priority_annotation(qs):
    return qs.annotate(
        priority_rank=Case(
            When(priority=Announcement.Priority.CRITICAL, then=0),
            When(priority=Announcement.Priority.HIGH, then=1),
            When(priority=Announcement.Priority.NORMAL, then=2),
            default=3,
            output_field=IntegerField(),
        )
    )


def active_announcements_for_user(user: User, *, limit: int = 5):
    if not user.is_authenticated or not user.tenant_id:
        return []

    dismissed = dismissed_announcement_ids(user)
    qs = _priority_annotation(
        _plant_filter(_base_announcement_queryset(tenant=user.tenant), user)
    )
    qs = qs.select_related("plant", "created_by").order_by(
        "-is_pinned",
        "priority_rank",
        "-publish_start",
    )
    if dismissed:
        qs = qs.exclude(pk__in=dismissed)

    results: list[Announcement] = []
    for announcement in qs:
        if not _matches_user_role(announcement, user):
            continue
        results.append(announcement)
        if len(results) >= limit:
            break
    return results


def announcements_for_user(user: User):
    if not user.is_authenticated or not user.tenant_id:
        return []

    qs = _priority_annotation(
        _plant_filter(_base_announcement_queryset(tenant=user.tenant), user)
    ).select_related("plant", "created_by").order_by(
        "-is_pinned",
        "priority_rank",
        "-publish_start",
    )
    return [item for item in qs if _matches_user_role(item, user)]


def get_announcement_for_user(user: User, pk: int) -> Announcement | None:
    return next(
        (item for item in announcements_for_user(user) if item.pk == pk),
        None,
    )


def dismiss_announcement(user: User, announcement: Announcement) -> None:
    AnnouncementDismissal.objects.get_or_create(
        announcement=announcement,
        user=user,
    )


def increment_announcement_views(announcement: Announcement) -> None:
    Announcement.objects.filter(pk=announcement.pk).update(
        view_count=announcement.view_count + 1
    )


def active_announcement_count(user: User) -> int:
    return len(active_announcements_for_user(user, limit=50))
