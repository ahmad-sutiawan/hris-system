"""Queryset scoping helpers for employee self-service API clients."""


def employee_scoped_queryset(user, qs, *, employee_field="employee"):
    if user.is_hr or user.is_admin:
        return qs
    profile = getattr(user, "employee_profile", None)
    if profile:
        return qs.filter(**{employee_field: profile})
    return qs.none()
