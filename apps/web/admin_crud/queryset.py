from django.db.models import Q

from apps.core.models import Plant, Tenant


def _model_has_field(model, field_name):
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def get_queryset(request, resource):
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
        return qs

    if model is type(user):
        if tenant:
            qs = qs.filter(tenant=tenant)
        return qs

    if resource.tenant_scoped and tenant and _model_has_field(model, "tenant"):
        qs = qs.filter(tenant=tenant)

    query = request.GET.get("q", "").strip()
    if query and resource.search_fields:
        condition = Q()
        for field_name in resource.search_fields:
            condition |= Q(**{f"{field_name}__icontains": query})
        qs = qs.filter(condition)

    return qs.order_by(*resource.order_by)


def get_cell_value(obj, attr_path: str):
    value = obj
    for part in attr_path.split("."):
        value = getattr(value, part, None)
        if value is None:
            return "-"
    if hasattr(value, "all"):
        return str(value)
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M") if hasattr(value, "hour") else value.strftime("%Y-%m-%d")
    if isinstance(value, bool):
        return "Ya" if value else "Tidak"
    return value


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

    instance.save()
    form.save_m2m()
    return instance
