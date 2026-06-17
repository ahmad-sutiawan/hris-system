"""
Central queryset optimization helpers — gunakan ini untuk mencegah N+1.

Pola:
  - select_related: ForeignKey / OneToOne (JOIN)
  - prefetch_related: reverse FK / M2M
  - only()/defer(): list view yang tidak butuh kolom berat (mis. audit changes)
"""


def employee_list_qs(qs):
    return qs.select_related(
        "plant",
        "legal_entity",
        "department",
        "job_position",
        "default_shift",
        "manager",
        "user",
    )


def payslip_list_qs(qs):
    return qs.select_related("employee", "payroll_run", "payroll_run__plant")


def timesheet_list_qs(qs):
    return qs.select_related("employee", "plant", "shift", "attendance_code")


def overtime_list_qs(qs):
    return qs.select_related("employee", "overtime_type", "approver")


def audit_log_list_qs(qs, *, include_changes: bool = False):
    qs = qs.select_related("user", "tenant")
    if not include_changes:
        qs = qs.defer("changes", "user_agent")
    return qs
