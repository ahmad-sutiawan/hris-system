from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.core.models import AuditLog
from apps.core.services.audit import diff_instance, log_audit
from apps.employees.models import Employee
from apps.attendance.models import OvertimeRequest
from apps.leave.models import LeaveRequest
from apps.payroll.models import PayrollRun, Payslip

_pre_save_cache = {}


def _cache_key(sender, instance):
    return (sender, instance.pk)


@receiver(pre_save)
def audit_pre_save(sender, instance, **kwargs):
    if sender is AuditLog:
        return
    if not getattr(instance, "pk", None):
        return
    if sender not in {Employee, LeaveRequest, OvertimeRequest, PayrollRun, Payslip}:
        return
    try:
        old = sender.objects.get(pk=instance.pk)
        _pre_save_cache[_cache_key(sender, instance)] = old
    except sender.DoesNotExist:
        pass


@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    if sender is AuditLog:
        return
    if sender not in {Employee, LeaveRequest, OvertimeRequest, PayrollRun, Payslip}:
        return

    if created:
        log_audit(AuditLog.Action.CREATE, instance)
        return

    old = _pre_save_cache.pop(_cache_key(sender, instance), None)
    changes = diff_instance(old, instance)
    if changes:
        log_audit(AuditLog.Action.UPDATE, instance, changes=changes)


@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    if sender is AuditLog:
        return
    if sender not in {Employee, LeaveRequest, OvertimeRequest, PayrollRun, Payslip}:
        return
    log_audit(AuditLog.Action.DELETE, instance)
