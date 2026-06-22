"""Payslip visibility rules — employees only see finalized payroll slips."""

from apps.payroll.models import PayrollRun


def restrict_payslip_visibility(qs, user):
    """HR/admin see all statuses; employees and managers only see finalized runs."""
    if user.is_hr or user.is_admin:
        return qs
    return qs.filter(payroll_run__status=PayrollRun.Status.FINALIZED)
