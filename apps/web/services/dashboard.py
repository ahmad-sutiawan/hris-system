from datetime import timedelta
import math

from django.db.models import Count, Max, Q

from apps.attendance.models import AttendanceRecord, DailyTimesheet, OvertimeRequest
from apps.core.models import Notification, User
from apps.employees.models import Employee
from apps.employees.services.onboarding import employee_leave_balances_summary
from apps.leave.models import LeaveRequest
from apps.payroll.models import PayrollRun, Payslip
from apps.shifts.models import ShiftAssignment


def _active_employees(user: User, tenant):
    qs = Employee.objects.filter(tenant=tenant).exclude(
        status__in=[Employee.Status.INACTIVE, Employee.Status.RESIGNED]
    )
    if user.plant_id and not user.is_admin:
        qs = qs.filter(plant=user.plant)
    return qs


def _plant_filter(user: User, qs):
    if user.plant_id and not user.is_admin:
        return qs.filter(plant=user.plant)
    return qs


def _latest_punch_photos(employee_ids: list[int], *, request=None) -> dict[int, str]:
    if not employee_ids:
        return {}

    latest_by_employee = dict(
        AttendanceRecord.objects.filter(employee_id__in=employee_ids)
        .exclude(check_in_photo="")
        .values("employee_id")
        .annotate(max_date=Max("work_date"))
        .values_list("employee_id", "max_date")
    )
    if not latest_by_employee:
        return {}

    pair_filter = Q()
    for employee_id, max_date in latest_by_employee.items():
        pair_filter |= Q(employee_id=employee_id, work_date=max_date)

    photos: dict[int, str] = {}
    for record in AttendanceRecord.objects.filter(pair_filter).only(
        "employee_id", "check_in_photo"
    ):
        if not record.check_in_photo or not record.check_in_photo.name:
            continue
        try:
            from apps.core.media_serving import build_media_url

            url = build_media_url(record.check_in_photo.name, request=request)
            if url:
                photos[record.employee_id] = url
        except Exception:
            continue
    return photos


def _employee_profile_photos(employee_ids: list[int], *, request=None) -> dict[int, str]:
    if not employee_ids:
        return {}

    from apps.employees.models import Employee
    from apps.employees.services.photo import employee_photo_url

    photos: dict[int, str] = {}
    for employee in Employee.objects.filter(id__in=employee_ids).only("id", "photo"):
        url = employee_photo_url(employee, request=request)
        if url:
            photos[employee.id] = url
    return photos


def _resolve_employee_photo_urls(employee_ids: list[int], *, request=None) -> dict[int, str]:
    photos = _employee_profile_photos(employee_ids, request=request)
    missing = [employee_id for employee_id in employee_ids if employee_id not in photos]
    if missing:
        punch_photos = _latest_punch_photos(missing, request=request)
        photos.update(punch_photos)
    return photos


def build_on_leave_today_items(*, user: User, tenant, today, request=None) -> list[dict]:
    """Karyawan aktif yang sedang cuti (semua jenis, approved) pada tanggal `today`."""
    active_ids = list(_active_employees(user, tenant).values_list("id", flat=True))
    if not active_ids:
        return []

    leave_requests = (
        LeaveRequest.objects.filter(
            tenant=tenant,
            status=LeaveRequest.Status.APPROVED,
            start_date__lte=today,
            end_date__gte=today,
            employee_id__in=active_ids,
        )
        .select_related("employee", "employee__department", "leave_type")
        .order_by("employee__full_name", "start_date")
    )

    employee_ids = []
    seen: set[int] = set()
    for request in leave_requests:
        if request.employee_id in seen:
            continue
        seen.add(request.employee_id)
        employee_ids.append(request.employee_id)

    photos = _resolve_employee_photo_urls(employee_ids, request=request)
    items: list[dict] = []
    seen.clear()
    for request in leave_requests:
        if request.employee_id in seen:
            continue
        seen.add(request.employee_id)
        items.append(
            {
                "employee": request.employee,
                "leave_request": request,
                "photo_url": photos.get(request.employee_id, ""),
            }
        )
    return items


def _attendance_rate(*, present: int, on_leave: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((present + on_leave) / total * 100, 1)


def _ring_segments(items: list[dict], colors: list[str]) -> list[dict]:
    total = sum(item["value"] for item in items) or 1
    offset = 0.0
    segments: list[dict] = []
    for index, item in enumerate(items):
        pct = item["value"] / total * 100
        segments.append(
            {
                **item,
                "color": colors[index % len(colors)],
                "start": round(offset, 2),
                "end": round(offset + pct, 2),
                "pct": round(pct, 1),
            }
        )
        offset += pct
    return segments


def _bar_rows(items: list[dict], *, limit: int = 8) -> tuple[list[dict], int]:
    rows = items[:limit]
    max_value = max((row["value"] for row in rows), default=0) or 1
    enriched = []
    for row in rows:
        enriched.append(
            {
                **row,
                "width_pct": round(row["value"] / max_value * 100),
            }
        )
    return enriched, max_value


_GAUGE_R = 40
_GAUGE_C = round(2 * 3.14159265 * _GAUGE_R, 2)


def _pct(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(value / total * 100, 1)


def _gauge_offset(pct: float) -> float:
    return round(_GAUGE_C * (1 - pct / 100), 2)


def _arc_dash(radius: float, pct: float, *, sweep: float = 0.72) -> tuple[float, float]:
    circumference = 2 * 3.14159265 * radius
    visible = circumference * sweep * min(pct, 100) / 100
    return round(visible, 2), round(circumference, 2)


def _sparkline_points(
    values: list[int],
    *,
    width: float = 300,
    height: float = 110,
    pad: float = 14,
    max_value: int,
) -> str:
    if not values:
        return ""
    span = max(len(values) - 1, 1)
    points: list[str] = []
    for index, value in enumerate(values):
        x = pad + index * ((width - pad * 2) / span)
        ratio = value / max_value if max_value else 0
        y = height - pad - ratio * (height - pad * 2)
        points.append(f"{round(x, 1)},{round(y, 1)}")
    return " ".join(points)


def _mini_sparkline(
    values: list[int],
    *,
    max_value: int,
    width: float = 48,
    height: float = 14,
    pad: float = 2,
) -> str:
    if not values:
        return ""
    span = max(len(values) - 1, 1)
    points: list[str] = []
    cap = max(max_value, max(values), 1)
    for index, value in enumerate(values):
        x = pad + index * ((width - pad * 2) / span)
        ratio = value / cap
        y = height - pad - ratio * (height - pad * 2)
        points.append(f"{round(x, 1)},{round(y, 1)}")
    return " ".join(points)


def _build_neo_visuals(
    *,
    stats_extra: dict,
    total_active: int,
    plant_rows: list[dict],
    plant_max: int,
    status_rows: list[dict],
    dept_rows: list[dict],
    dept_max: int,
    week: list[dict],
    week_max: int,
    today,
    pending_leave: int,
    pending_overtime: int,
    employee_count: int,
    attendance_rate: float,
    today_timesheets: int = 0,
    draft_payroll: int = 0,
) -> dict:
    gauge_tones = ["cyan", "magenta", "gold"]
    gauges = []
    for tone, label, value in zip(
        gauge_tones,
        ["Hadir", "Cuti", "Belum Hadir"],
        [
            stats_extra["present_today"],
            stats_extra["on_leave_today"],
            stats_extra["absent_today"],
        ],
    ):
        pct = _pct(value, total_active)
        gauges.append(
            {
                "label": label,
                "value": value,
                "pct": pct,
                "offset": _gauge_offset(pct),
                "tone": tone,
            }
        )

    diverging_plants = []
    for index, row in enumerate(plant_rows[:6]):
        diverging_plants.append(
            {
                **row,
                "bar_pct": round(row["value"] / plant_max * 100) if plant_max else 0,
                "lane": index,
            }
        )

    arc_radii = [44, 36, 28, 22, 18]
    radial_arcs = []
    for index, row in enumerate(status_rows[:5]):
        radius = arc_radii[index % len(arc_radii)]
        pct = _pct(row["value"], total_active)
        dash, circ = _arc_dash(radius, pct)
        radial_arcs.append(
            {
                "label": row["label"],
                "value": row["value"],
                "pct": pct,
                "r": radius,
                "dash": dash,
                "circ": circ,
                "tone": ["cyan", "magenta", "gold", "purple", "orange"][index % 5],
            }
        )

    diverging_depts = []
    for index, row in enumerate(dept_rows[:8]):
        diverging_depts.append(
            {
                **row,
                "left_pct": round(row["value"] / dept_max * 46) if dept_max else 0,
                "right_pct": round(row["value"] / dept_max * 46) if dept_max else 0,
                "lane": index,
            }
        )

    counts = [day["count"] for day in week]
    trend_lines = [
        {"tone": "cyan", "points": _sparkline_points(counts, max_value=week_max, height=90)},
        {
            "tone": "magenta",
            "points": _sparkline_points(
                [max(0, value - max(1, week_max // 8)) for value in counts],
                max_value=week_max,
                height=90,
            ),
        },
        {
            "tone": "gold",
            "points": _sparkline_points(
                [min(week_max, value + max(1, week_max // 10)) for value in counts],
                max_value=week_max,
                height=90,
            ),
        },
    ]
    highlight_index = next(
        (index for index, day in enumerate(week) if day["date"] == today),
        len(week) - 1,
    )
    highlight_x = 14 + highlight_index * (272 / max(len(week) - 1, 1))
    highlight_value = counts[highlight_index] if counts else 0
    trend_points = []
    for index, day in enumerate(week):
        x = 14 + index * (272 / max(len(week) - 1, 1))
        count = day["count"]
        ratio = count / week_max if week_max else 0
        y = 90 - 14 - ratio * (90 - 28)
        trend_points.append(
            {
                "x": round(x, 1),
                "y": round(y, 1),
                "label": day["date"].strftime("%a"),
                "value": count,
                "is_today": day["date"] == today,
            }
        )

    kpi_tiles = [
        {
            "label": "Karyawan Aktif",
            "value": employee_count,
            "tone": "cyan",
            "pct": 100,
            "icon": "WF",
            "spark_points": _mini_sparkline(counts[-5:] or [employee_count], max_value=max(week_max, employee_count, 1)),
        },
        {
            "label": "Hadir Hari Ini",
            "value": stats_extra["present_today"],
            "tone": "green",
            "pct": _pct(stats_extra["present_today"], total_active),
            "icon": "IN",
            "spark_points": _mini_sparkline(counts[-5:] if counts else [0], max_value=week_max or 1),
        },
        {
            "label": "Sedang Cuti",
            "value": stats_extra["on_leave_today"],
            "tone": "magenta",
            "pct": _pct(stats_extra["on_leave_today"], total_active),
            "icon": "LV",
            "spark_points": _mini_sparkline(
                [stats_extra["on_leave_today"]] * 5,
                max_value=max(stats_extra["on_leave_today"], 1),
            ),
        },
        {
            "label": "Belum Hadir",
            "value": stats_extra["absent_today"],
            "tone": "orange",
            "pct": _pct(stats_extra["absent_today"], total_active),
            "icon": "AB",
            "spark_points": _mini_sparkline(
                [stats_extra["absent_today"]] * 5,
                max_value=max(stats_extra["absent_today"], 1),
            ),
        },
        {
            "label": "Cuti Pending",
            "value": pending_leave,
            "tone": "gold",
            "pct": min(100, round(pending_leave / max(employee_count, 1) * 100)),
            "icon": "PL",
            "spark_points": _mini_sparkline([pending_leave] * 5, max_value=max(pending_leave, 1)),
        },
        {
            "label": "Lembur Pending",
            "value": pending_overtime,
            "tone": "purple",
            "pct": min(100, round(pending_overtime / max(employee_count, 1) * 100)),
            "icon": "OT",
            "spark_points": _mini_sparkline([pending_overtime] * 5, max_value=max(pending_overtime, 1)),
        },
        {
            "label": "Timesheet Hari Ini",
            "value": today_timesheets,
            "tone": "cyan",
            "pct": _pct(today_timesheets, employee_count),
            "icon": "TS",
            "spark_points": _mini_sparkline(counts[-5:] if counts else [0], max_value=week_max or 1),
        },
        {
            "label": "Payroll Draft",
            "value": draft_payroll,
            "tone": "gold",
            "pct": min(100, draft_payroll * 20),
            "icon": "PR",
            "spark_points": _mini_sparkline([draft_payroll] * 5, max_value=max(draft_payroll, 1)),
        },
    ]

    radar_axes = [
        {"label": "Workforce", "value": employee_count},
        {"label": "Hadir", "value": stats_extra["present_today"]},
        {"label": "Cuti", "value": stats_extra["on_leave_today"]},
        {"label": "Cuti Pending", "value": pending_leave},
        {"label": "Lembur Pending", "value": pending_overtime},
    ]
    radar_max = max((axis["value"] for axis in radar_axes), default=1) or 1
    radar_points = []
    axis_count = len(radar_axes)
    for index, axis in enumerate(radar_axes):
        angle = -1.5708 + index * (2 * 3.14159265 / axis_count)
        ratio = axis["value"] / radar_max
        x = 60 + 42 * ratio * math.cos(angle)
        y = 60 + 42 * ratio * math.sin(angle)
        radar_points.append(
            {
                **axis,
                "pct": round(ratio * 100),
                "x": round(x, 1),
                "y": round(y, 1),
                "lx": round(60 + 50 * math.cos(angle), 1),
                "ly": round(60 + 50 * math.sin(angle), 1),
            }
        )
    radar_poly = " ".join(f"{point['x']},{point['y']}" for point in radar_points)

    return {
        "gauges": gauges,
        "diverging_plants": diverging_plants,
        "radial_arcs": radial_arcs,
        "diverging_depts": diverging_depts,
        "trend_lines": trend_lines,
        "trend_highlight": {
            "x": round(highlight_x, 1),
            "value": highlight_value,
            "label": week[highlight_index]["date"].strftime("%a") if week else "",
        },
        "diamonds": [
            {
                "code": "01",
                "label": "Cuti Pending",
                "value": pending_leave,
                "tone": "cyan",
            },
            {
                "code": "02",
                "label": "Lembur Pending",
                "value": pending_overtime,
                "tone": "magenta",
            },
            {
                "code": "03",
                "label": "Total Antrian",
                "value": pending_leave + pending_overtime,
                "tone": "gold",
            },
        ],
        "radar_points": radar_points,
        "radar_poly": radar_poly,
        "attendance_rate": attendance_rate,
        "headline_total": total_active,
        "kpi_tiles": kpi_tiles,
        "trend_points": trend_points,
    }


def empty_dashboard_context(*, user=None) -> dict:
    """Default dashboard context — aman untuk template jika query gagal."""
    return {
        "show_ops": bool(user and user.is_hr),
        "stats_extra": {
            "present_today": 0,
            "on_leave_today": 0,
            "absent_today": 0,
        },
        "analytics": {
            "attendance_rate": 0.0,
            "chart_attendance_today": [],
            "chart_employee_status": [],
            "chart_by_plant": [],
            "chart_top_departments": [],
            "chart_pending_ops": [],
            "heatmap_week": [],
            "chart_week": [],
            "attendance_segments": [],
            "pending_segments": [],
            "status_rows": [],
            "plant_rows": [],
            "dept_rows": [],
            "status_max": 1,
            "plant_max": 1,
            "dept_max": 1,
            "neo": {
                "kpi_tiles": [],
                "gauges": [],
                "diverging_plants": [],
                "radial_arcs": [],
                "diverging_depts": [],
                "trend_lines": [],
                "trend_points": [],
                "trend_highlight": {"x": 0, "value": 0, "label": ""},
                "diamonds": [],
                "radar_points": [],
                "radar_poly": "",
                "attendance_rate": 0.0,
                "headline_total": 0,
            },
        },
        "recent_notifications": [],
        "pending_leave_items": [],
        "pending_overtime_items": [],
        "attendance_week": [],
        "attendance_week_max": 1,
        "leave_balances": [],
        "today_shift": None,
        "latest_payroll": None,
        "latest_payslip": None,
        "profile_summary": None,
        "on_leave_today_items": [],
        "pending_leave_count": 0,
        "pending_overtime_count": 0,
    }


def build_dashboard_context(*, user: User, tenant, today, profile, request=None):
    """Aggregate dashboard widgets from existing HRIS data."""
    context = empty_dashboard_context(user=user)

    if not tenant:
        return context

    context["recent_notifications"] = list(
        Notification.objects.filter(user=user).order_by("-created_at")[:5]
    )

    active_emp = _active_employees(user, tenant)
    active_count = active_emp.count()
    active_id_subq = active_emp.values("id")

    on_leave_today_items = build_on_leave_today_items(
        user=user,
        tenant=tenant,
        today=today,
        request=request,
    )
    on_leave_ids = {item["employee"].id for item in on_leave_today_items}
    context["on_leave_today_items"] = on_leave_today_items

    present_qs = _plant_filter(
        user,
        AttendanceRecord.objects.filter(
            tenant=tenant,
            work_date=today,
            check_in__isnull=False,
            employee_id__in=active_id_subq,
        ),
    )
    present_ids = set(present_qs.values_list("employee_id", flat=True))

    context["stats_extra"] = {
        "present_today": len(present_ids),
        "on_leave_today": len(on_leave_ids),
        "absent_today": max(
            0,
            active_count - len(present_ids) - len(on_leave_ids),
        ),
    }

    stats_extra = context["stats_extra"]
    total_active = active_count
    context["analytics"] = {
        "attendance_rate": _attendance_rate(
            present=stats_extra["present_today"],
            on_leave=stats_extra["on_leave_today"],
            total=total_active,
        ),
        "chart_attendance_today": [
            {"label": "Hadir", "value": stats_extra["present_today"]},
            {"label": "Cuti", "value": stats_extra["on_leave_today"]},
            {"label": "Belum Hadir", "value": stats_extra["absent_today"]},
        ],
        "chart_employee_status": [
            {
                "label": row["status_employee"] or "Tidak diisi",
                "value": row["c"],
            }
            for row in active_emp.values("status_employee")
            .annotate(c=Count("id"))
            .order_by("-c")[:6]
        ],
        "chart_by_plant": [
            {
                "label": row["plant__code"] or "—",
                "name": row["plant__name"] or "—",
                "value": row["c"],
            }
            for row in active_emp.values("plant__code", "plant__name")
            .annotate(c=Count("id"))
            .order_by("-c")[:8]
        ],
        "chart_top_departments": [
            {
                "label": (row["department__name"] or "—")[:28],
                "value": row["c"],
            }
            for row in active_emp.values("department__name")
            .annotate(c=Count("id"))
            .order_by("-c")[:8]
        ],
        "chart_pending_ops": [
            {"label": "Cuti", "value": context.get("pending_leave_count", 0)},
            {"label": "Lembur", "value": context.get("pending_overtime_count", 0)},
        ],
        "heatmap_week": [],
    }

    week = []
    week_max = 0
    week_start = today - timedelta(days=6)
    week_count_map = dict(
        _plant_filter(
            user,
            DailyTimesheet.objects.filter(
                tenant=tenant,
                work_date__gte=week_start,
                work_date__lte=today,
                employee_id__in=active_id_subq,
            ),
        )
        .values("work_date")
        .annotate(c=Count("id"))
        .values_list("work_date", "c")
    )
    for offset in range(6, -1, -1):
        work_date = today - timedelta(days=offset)
        count = week_count_map.get(work_date, 0)
        week_max = max(week_max, count)
        week.append({"date": work_date, "count": count})
    context["attendance_week"] = week
    context["attendance_week_max"] = week_max or 1
    context["analytics"]["heatmap_week"] = [
        {
            "label": day["date"].strftime("%a"),
            "date": day["date"].isoformat(),
            "value": day["count"],
            "intensity": round(day["count"] / (week_max or 1) * 100),
            "is_today": day["date"] == today,
        }
        for day in week
    ]
    context["analytics"]["chart_week"] = [
        {
            "label": day["date"].strftime("%a"),
            "value": day["count"],
            "is_today": day["date"] == today,
        }
        for day in week
    ]

    pending_leave_count = LeaveRequest.objects.filter(
        tenant=tenant,
        status=LeaveRequest.Status.PENDING,
        employee_id__in=active_id_subq,
    ).count()
    pending_overtime_count = OvertimeRequest.objects.filter(
        tenant=tenant,
        status=OvertimeRequest.Status.PENDING,
        employee_id__in=active_id_subq,
    ).count()
    context["pending_leave_count"] = pending_leave_count
    context["pending_overtime_count"] = pending_overtime_count
    context["analytics"]["chart_pending_ops"] = [
        {"label": "Cuti", "value": pending_leave_count},
        {"label": "Lembur", "value": pending_overtime_count},
    ]

    attendance_segments = _ring_segments(
        context["analytics"]["chart_attendance_today"],
        ["#059669", "#3269cc", "#dc2626"],
    )
    status_rows, status_max = _bar_rows(context["analytics"]["chart_employee_status"])
    plant_rows, plant_max = _bar_rows(context["analytics"]["chart_by_plant"])
    dept_rows, dept_max = _bar_rows(context["analytics"]["chart_top_departments"])
    pending_segments = _ring_segments(
        context["analytics"]["chart_pending_ops"],
        ["#fbd02f", "#3428a8"],
    )
    context["analytics"]["attendance_segments"] = attendance_segments
    context["analytics"]["pending_segments"] = pending_segments
    context["analytics"]["status_rows"] = status_rows
    context["analytics"]["plant_rows"] = plant_rows
    context["analytics"]["dept_rows"] = dept_rows
    context["analytics"]["status_max"] = status_max
    context["analytics"]["plant_max"] = plant_max
    context["analytics"]["dept_max"] = dept_max
    timesheet_today = _plant_filter(
        user,
        DailyTimesheet.objects.filter(
            tenant=tenant,
            work_date=today,
            employee_id__in=active_id_subq,
        ),
    ).count()
    draft_payroll_qs = PayrollRun.objects.filter(
        tenant=tenant,
        status=PayrollRun.Status.DRAFT,
    )
    if user.plant_id and not user.is_admin:
        draft_payroll_qs = draft_payroll_qs.filter(plant=user.plant)
    draft_payroll_count = draft_payroll_qs.count()

    context["analytics"]["neo"] = _build_neo_visuals(
        stats_extra=context["stats_extra"],
        total_active=total_active,
        plant_rows=plant_rows,
        plant_max=plant_max,
        status_rows=status_rows,
        dept_rows=dept_rows,
        dept_max=dept_max,
        week=week,
        week_max=week_max or 1,
        today=today,
        pending_leave=pending_leave_count,
        pending_overtime=pending_overtime_count,
        employee_count=total_active,
        attendance_rate=context["analytics"]["attendance_rate"],
        today_timesheets=timesheet_today,
        draft_payroll=draft_payroll_count,
    )

    if user.is_hr:
        context["pending_leave_items"] = list(
            LeaveRequest.objects.filter(
                tenant=tenant,
                status=LeaveRequest.Status.PENDING,
                employee_id__in=active_id_subq,
            )
            .select_related("employee", "leave_type")
            .order_by("-created_at")[:5]
        )
        context["pending_overtime_items"] = list(
            OvertimeRequest.objects.filter(
                tenant=tenant,
                status=OvertimeRequest.Status.PENDING,
                employee_id__in=active_id_subq,
            )
            .select_related("employee", "overtime_type")
            .order_by("-created_at")[:5]
        )
        payroll_qs = PayrollRun.objects.filter(tenant=tenant)
        if user.plant_id and not user.is_admin:
            payroll_qs = payroll_qs.filter(plant=user.plant)
        context["latest_payroll"] = payroll_qs.select_related("plant").order_by(
            "-period_start"
        ).first()

    if profile:
        context["leave_balances"] = employee_leave_balances_summary(profile)
        context["today_shift"] = (
            ShiftAssignment.objects.filter(employee=profile, work_date=today)
            .select_related("shift", "employee", "employee__plant")
            .first()
        )
        context["latest_payslip"] = (
            Payslip.objects.filter(employee=profile)
            .select_related("payroll_run", "payroll_run__plant")
            .order_by("-payroll_run__period_start")
            .first()
        )
        job = profile.job_position
        dept = profile.department
        context["profile_summary"] = {
            "employee_id": profile.employee_id,
            "department": dept.name if dept else "—",
            "position": job.title if job else "—",
            "ptkp": profile.tax_status or "—",
            "plant": profile.plant.name if profile.plant_id else "—",
            "status": profile.get_status_display(),
        }

    return context
