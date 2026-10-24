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
        "plant__parent",
        "legal_entity",
        "department",
        "job_position",
        "job_level",
        "default_shift",
        "manager",
        "user",
        "religion",
        "blood_type",
        "nationality",
        "currency",
        "payment_schedule",
        "approval_line",
        "grade",
        "talenta_class",
        "cost_center",
        "cost_center_category",
        "sbu",
        "employee_tax_status_master",
        "tax_config_master",
    )


def payslip_list_qs(qs):
    return qs.select_related("employee", "payroll_run", "payroll_run__plant")


def timesheet_list_qs(qs):
    return qs.select_related(
        "employee",
        "employee__department",
        "employee__job_position",
        "plant",
        "shift",
        "attendance_code",
    )


def overtime_list_qs(qs):
    return qs.select_related("employee", "overtime_type", "approver")


def audit_log_list_qs(qs, *, include_changes: bool = False):
    qs = qs.select_related("user", "tenant")
    if not include_changes:
        qs = qs.defer("changes", "user_agent")
    return qs
