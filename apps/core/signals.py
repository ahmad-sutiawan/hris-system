from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.attendance.services.geo import invalidate_geo_cache
from apps.core.models import AuditLog, Plant, PunchLocation
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


_PLANT_GEO_FIELDS = ("latitude", "longitude", "geo_fence_radius_m")


@receiver(pre_save, sender=PunchLocation)
def remember_punch_location_plant(sender, instance, **kwargs):
    if not instance.pk:
        instance._geo_old_plant_id = None
        return
    instance._geo_old_plant_id = (
        PunchLocation.objects.filter(pk=instance.pk).values_list("plant_id", flat=True).first()
    )


@receiver(post_save, sender=PunchLocation)
def invalidate_punch_location_cache_on_save(sender, instance, **kwargs):
    invalidate_geo_cache(tenant_id=instance.tenant_id, plant_id=instance.plant_id)
    old_plant_id = getattr(instance, "_geo_old_plant_id", None)
    if old_plant_id and old_plant_id != instance.plant_id:
        invalidate_geo_cache(tenant_id=instance.tenant_id, plant_id=old_plant_id)


@receiver(post_delete, sender=PunchLocation)
def invalidate_punch_location_cache_on_delete(sender, instance, **kwargs):
    invalidate_geo_cache(tenant_id=instance.tenant_id, plant_id=instance.plant_id)


@receiver(pre_save, sender=Plant)
def remember_plant_geo(sender, instance, **kwargs):
    if not instance.pk:
        instance._geo_old = None
        return
    instance._geo_old = Plant.objects.filter(pk=instance.pk).values(*_PLANT_GEO_FIELDS).first()


@receiver(post_save, sender=Plant)
def invalidate_plant_geo_cache(sender, instance, created, **kwargs):
    old = getattr(instance, "_geo_old", None)
    changed = created or old is None or any(
        old.get(field) != getattr(instance, field) for field in _PLANT_GEO_FIELDS
    )
    if not changed:
        return
    invalidate_geo_cache(tenant_id=instance.tenant_id, plant_id=instance.pk)
    if instance.parent_id:
        invalidate_geo_cache(tenant_id=instance.tenant_id, plant_id=instance.parent_id)


@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    if sender is AuditLog:
        return
    if sender not in {Employee, LeaveRequest, OvertimeRequest, PayrollRun, Payslip}:
        return
    log_audit(AuditLog.Action.DELETE, instance)
