"""Web list view orchestration — pagination, export, shared template context."""

from django.http import HttpResponse

from apps.core.listing import (
    DEFAULT_PAGE_SIZE,
    export_format_requested,
    list_pagination_context,
    paginate_queryset,
    parse_list_filters,
)
from apps.core.xlsx_io import normalize_xlsx_filename, xlsx_http_response


def resolve_list(request, queryset, *, export_filename: str, export_fn, per_page: int | None = None):
    """
    Return (HttpResponse|None, context_dict).

    If export is requested, returns (HttpResponse, None).
    Otherwise returns (None, pagination context including page_obj).
    """
    filters = parse_list_filters(request, per_page=per_page or DEFAULT_PAGE_SIZE)
    if export_format_requested(request):
        content = export_fn(queryset)
        return xlsx_http_response(content, normalize_xlsx_filename(export_filename)), None

    page_obj = paginate_queryset(queryset, filters)
    context = list_pagination_context(request, page_obj, filters)
    context["page_obj"] = page_obj
    return None, context
