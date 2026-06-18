from django.db.models import Q

from apps.core.listing import ListFilters, apply_datetime_range
from apps.core.models import Plant, Tenant


def _model_has_field(model, field_name):
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def get_queryset(request, resource, filters: ListFilters | None = None):
    model = resource.model
    qs = model.objects.all()

    if resource.select_related:
        qs = qs.select_related(*resource.select_related)

    user = request.user
    tenant = user.tenant

    if model is Tenant:
        if tenant:
            qs = qs.filter(pk=tenant.pk)
        return qs

    if model is Plant:
        if tenant:
            qs = qs.filter(tenant=tenant)
        if resource.slug == "plants":
            qs = qs.filter(entity_type=Plant.EntityType.PT)
        elif resource.slug == "branches":
            qs = qs.filter(entity_type=Plant.EntityType.BRANCH)
        return qs

    if model is type(user):
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs

    if resource.tenant_scoped and tenant and _model_has_field(model, "tenant"):
        qs = qs.filter(tenant=tenant)

    filters = filters or ListFilters(q=request.GET.get("q", "").strip())
    if filters.q and resource.search_fields:
        condition = Q()
        for field_name in resource.search_fields:
            condition |= Q(**{f"{field_name}__icontains": filters.q})
        qs = qs.filter(condition)
    if _model_has_field(model, "created_at"):
        qs = apply_datetime_range(
            qs,
            date_from=filters.date_from,
            date_to=filters.date_to,
            field_name="created_at",
        )

    return qs.order_by(*resource.order_by)


def get_cell_value(obj, attr_path: str):
    from apps.web.formatting import format_cell_value

    value = obj
    for part in attr_path.split("."):
        value = getattr(value, part, None)
        if value is None:
            return "-"
    return format_cell_value(value, attr_path)


def save_instance(form, request, resource):
    instance = form.save(commit=False)
    user = request.user

    if resource.model is Tenant:
        return instance

    if resource.model is Plant and not instance.tenant_id:
        instance.tenant = user.tenant

    if resource.model is type(user) and not instance.tenant_id:
        instance.tenant = user.tenant

    if resource.tenant_scoped and _model_has_field(resource.model, "tenant") and not instance.tenant_id:
        instance.tenant = user.tenant

    from apps.core.models import Announcement

    if resource.model is Announcement and not instance.created_by_id:
        instance.created_by = user

    instance.save()
    form.save_m2m()
    return instance
