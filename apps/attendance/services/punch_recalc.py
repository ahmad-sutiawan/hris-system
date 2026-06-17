"""Schedule daily timesheet recalculation after punch — sync or async via RQ."""

from __future__ import annotations

import logging
from datetime import date

from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)


def _async_enabled() -> bool:
    return bool(getattr(settings, "HRIS_PUNCH_ASYNC_RECALC", False))


def schedule_daily_timesheet_recalc(employee_id: int, work_date: date) -> None:
    """
    Queue or run timesheet recalculation after punch commits.

    Production (Redis + RQ): enqueue on ``punch`` queue — keeps CI/CO response fast.
    Dev/test fallback: synchronous recalc (same semantics, no worker required).
    """
    if _async_enabled():
        work_date_str = work_date.isoformat()
        job_id = f"ts-{employee_id}-{work_date_str}"

        def _enqueue() -> None:
            try:
                import django_rq
            except ImportError:
                logger.warning("django_rq not installed — falling back to sync recalc")
                _run_sync(employee_id, work_date)
                return

            queue = django_rq.get_queue("punch")
            try:
                queue.enqueue(
                    "apps.attendance.tasks.recalculate_timesheet_job",
                    employee_id,
                    work_date_str,
                    job_id=job_id,
                    job_timeout=120,
                    result_ttl=300,
                    failure_ttl=3600,
                )
            except Exception:
                logger.exception(
                    "RQ enqueue failed for employee=%s date=%s — sync fallback",
                    employee_id,
                    work_date_str,
                )
                _run_sync(employee_id, work_date)

        transaction.on_commit(_enqueue)
        return

    _run_sync(employee_id, work_date)


def _run_sync(employee_id: int, work_date: date) -> None:
    from apps.attendance.services.timesheet import recalculate_daily_timesheet
    from apps.employees.models import Employee

    employee = Employee.objects.select_related("tenant", "plant").get(pk=employee_id)
    recalculate_daily_timesheet(employee, work_date)
