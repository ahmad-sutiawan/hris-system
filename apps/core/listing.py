"""Shared list filtering, pagination, and CSV export helpers."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from io import StringIO
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.http import HttpResponse
from django.utils import timezone


DEFAULT_PAGE_SIZE = 25
MAX_EXPORT_ROWS = 10_000
PAGE_PARAM = "page"
EXPORT_PARAM = "export"


@dataclass
class ListFilters:
    q: str = ""
    date_from: str = ""
    date_to: str = ""
    job_position: str = ""
    department: str = ""
    job_level: str = ""
    page: int = 1
    per_page: int = DEFAULT_PAGE_SIZE

    @property
    def has_filters(self) -> bool:
        return bool(
            self.q
            or self.date_from
            or self.date_to
            or self.job_position
            or self.department
            or self.job_level
        )


def parse_list_filters(request, *, per_page: int = DEFAULT_PAGE_SIZE) -> ListFilters:
    page_raw = request.GET.get(PAGE_PARAM, "1")
    try:
        page = max(1, int(page_raw))
    except (TypeError, ValueError):
        page = 1
    return ListFilters(
        q=request.GET.get("q", "").strip(),
        date_from=request.GET.get("date_from", "").strip(),
        date_to=request.GET.get("date_to", "").strip(),
        job_position=(
            request.GET.get("job_position", "").strip()
            or request.GET.get("role", "").strip()
        ),
        department=request.GET.get("department", "").strip(),
        job_level=request.GET.get("job_level", "").strip(),
        page=page,
        per_page=per_page,
    )


def _parse_iso_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def apply_date_field_range(qs, *, date_from: str, date_to: str, field_name: str):
    """Filter queryset on a DateField (inclusive range)."""
    start = _parse_iso_date(date_from)
    end = _parse_iso_date(date_to)
    if start:
        qs = qs.filter(**{f"{field_name}__gte": start})
    if end:
        qs = qs.filter(**{f"{field_name}__lte": end})
    return qs


def apply_datetime_range(qs, *, date_from: str, date_to: str, field_name: str = "created_at"):
    """Filter queryset on a DateTimeField using date-only GET params."""
    start = _parse_iso_date(date_from)
    end = _parse_iso_date(date_to)
    if start:
        qs = qs.filter(**{f"{field_name}__date__gte": start})
    if end:
        qs = qs.filter(**{f"{field_name}__date__lte": end})
    return qs


def apply_period_overlap(qs, *, date_from: str, date_to: str, start_field: str, end_field: str):
    """Keep rows whose [start_field, end_field] overlaps [date_from, date_to]."""
    start = _parse_iso_date(date_from)
    end = _parse_iso_date(date_to)
    if start:
        qs = qs.filter(**{f"{end_field}__gte": start})
    if end:
        qs = qs.filter(**{f"{start_field}__lte": end})
    return qs


def paginate_queryset(qs, filters: ListFilters):
    paginator = Paginator(qs, filters.per_page)
    return paginator.get_page(filters.page)


def build_filter_query(request, *, exclude: tuple[str, ...] = (PAGE_PARAM, EXPORT_PARAM)) -> str:
    params = []
    for key, values in request.GET.lists():
        if key in exclude:
            continue
        for value in values:
            if value != "":
                params.append((key, value))
    return urlencode(params)


def list_pagination_context(request, page_obj, filters: ListFilters) -> dict:
    paginator = page_obj.paginator
    start_index = 0
    end_index = 0
    if paginator.count:
        start_index = page_obj.start_index()
        end_index = page_obj.end_index()
    return {
        "page_obj": page_obj,
        "paginator": paginator,
        "search_query": filters.q,
        "date_from": filters.date_from,
        "date_to": filters.date_to,
        "result_count": paginator.count,
        "page_start": start_index,
        "page_end": end_index,
        "filter_query": build_filter_query(request),
        "has_list_filters": filters.has_filters,
    }


def queryset_to_csv(rows, headers: list[str], row_builder) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row_builder(row))
    return buffer.getvalue()


def csv_http_response(content: str, filename: str) -> HttpResponse:
    bom = "\ufeff"
    response = HttpResponse(bom + content, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def maybe_export_csv(request, qs, *, filename: str, headers: list[str], row_builder):
    if request.GET.get(EXPORT_PARAM) != "csv":
        return None
    rows = qs[:MAX_EXPORT_ROWS]
    content = queryset_to_csv(rows, headers, row_builder)
    return csv_http_response(content, filename)


def format_dt(value: datetime | None) -> str:
    if not value:
        return ""
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime("%Y-%m-%d %H:%M")


def format_date(value: date | None) -> str:
    return value.isoformat() if value else ""
