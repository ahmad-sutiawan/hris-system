"""Queryset scoping helpers for employee self-service API clients."""

from django.db.models import Q

from apps.core.models import User


def employee_scoped_queryset(user, qs, *, employee_field="employee"):
    if user.is_hr or user.is_admin:
        return qs

    profile = getattr(user, "employee_profile", None)
    if user.role == User.Role.MANAGER and profile:
        return qs.filter(
            Q(**{employee_field: profile})
            | Q(**{f"{employee_field}__manager": profile})
        )

    if profile:
        return qs.filter(**{employee_field: profile})
    return qs.none()
