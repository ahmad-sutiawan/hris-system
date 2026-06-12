"""Web list view orchestration — pagination, export, shared template context."""

from django.http import HttpResponse

from apps.core.listing import (
    DEFAULT_PAGE_SIZE,
    csv_http_response,
    list_pagination_context,
    paginate_queryset,
    parse_list_filters,
)


def resolve_list(request, queryset, *, export_filename: str, export_fn, per_page: int | None = None):
    """
    Return (HttpResponse|None, context_dict).

    If export is requested, returns (HttpResponse, None).
    Otherwise returns (None, pagination context including page_obj).
    """
    filters = parse_list_filters(request, per_page=per_page or DEFAULT_PAGE_SIZE)
    if request.GET.get("export") == "csv":
        content = export_fn(queryset)
        return csv_http_response(content, export_filename), None

    page_obj = paginate_queryset(queryset, filters)
    context = list_pagination_context(request, page_obj, filters)
    context["page_obj"] = page_obj
    return None, context
