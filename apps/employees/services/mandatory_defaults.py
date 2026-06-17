"""Default values for mandatory employee fields (alignment HR Jun 2026)."""

from __future__ import annotations

from django.utils import timezone

from apps.employees.models import Employee

NA = "N/A"

TEXT_DEFAULTS = (
    "nik",
    "email",
    "phone",
    "address",
    "mother_name",
    "birth_place",
    "tax_status",
    "npwp",
    "bank_name",
    "bank_account_number",
    "bank_account_name",
    "bpjs_kesehatan_number",
    "bpjs_ketenagakerjaan_number",
)


def apply_mandatory_defaults(employee: Employee, *, fill_fk: bool = True) -> bool:
    """
    Fill blank mandatory fields with N/A (and sensible FK/date defaults when fill_fk=True).
    Returns True if any field was changed.
    """
    changed = False

    for field in TEXT_DEFAULTS:
        if not (getattr(employee, field) or "").strip():
            setattr(employee, field, NA)
            changed = True

    if not employee.gender:
        employee.gender = Employee.Gender.NA
        changed = True
    if not employee.marital_status:
        employee.marital_status = Employee.MaritalStatus.NA
        changed = True

    if not employee.join_date:
        employee.join_date = (
            timezone.localdate(employee.created_at)
            if employee.created_at
            else timezone.localdate()
        )
        changed = True

    if fill_fk and employee.plant_id:
        if not employee.department_id:
            from apps.organization.models import Department

            dept = Department.objects.filter(
                tenant=employee.tenant,
                plant=employee.plant,
                is_active=True,
            ).first()
            if dept:
                employee.department = dept
                changed = True

        if not employee.job_position_id:
            from apps.organization.models import JobPosition

            job = JobPosition.objects.filter(
                tenant=employee.tenant,
                plant=employee.plant,
                is_active=True,
            ).first()
            if job:
                employee.job_position = job
                changed = True

        if not employee.job_level_id:
            from apps.organization.models import JobLevel

            level = JobLevel.objects.filter(
                tenant=employee.tenant,
                is_active=True,
            ).order_by("rank").first()
            if level:
                employee.job_level = level
                changed = True

        if not employee.manager_id:
            from apps.core.models import User

            manager = (
                Employee.objects.filter(
                    tenant=employee.tenant,
                    plant=employee.plant,
                    user__role=User.Role.MANAGER,
                )
                .exclude(pk=employee.pk)
                .first()
            )
            if not manager:
                manager = (
                    Employee.objects.filter(tenant=employee.tenant, plant=employee.plant)
                    .exclude(pk=employee.pk)
                    .first()
                )
            if manager:
                employee.manager = manager
                changed = True

    return changed


def backfill_all_employees(*, tenant=None) -> dict:
    qs = Employee.objects.all()
    if tenant:
        qs = qs.filter(tenant=tenant)
    updated = 0
    for employee in qs.iterator():
        if apply_mandatory_defaults(employee, fill_fk=True):
            employee.save()
            updated += 1
    return {"updated": updated, "total": qs.count()}
