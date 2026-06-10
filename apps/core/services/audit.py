from apps.core.context import get_audit_context
from apps.core.models import AuditLog


SENSITIVE_FIELDS = {
    "employee": {"nik", "npwp", "bank_account_number", "base_salary"},
    "user": {"password"},
}


def _model_label(instance):
    return instance._meta.label_lower


def _tenant_for(instance):
    if hasattr(instance, "tenant_id") and instance.tenant_id:
        return instance.tenant
    if hasattr(instance, "employee_id") and instance.employee_id:
        return instance.employee.tenant
    if hasattr(instance, "payroll_run_id") and instance.payroll_run_id:
        return instance.payroll_run.tenant
    return None


def _mask_changes(model_label, changes):
    field_set = SENSITIVE_FIELDS.get(model_label.split(".")[-1], set())
    masked = {}
    for field, value in changes.items():
        if field in field_set:
            masked[field] = "***"
        else:
            masked[field] = value
    return masked


def log_audit(action, instance, *, changes=None):
    tenant = _tenant_for(instance)
    if not tenant:
        return

    ctx = get_audit_context()
    AuditLog.objects.create(
        tenant=tenant,
        user=ctx.get("user"),
        action=action,
        model_name=_model_label(instance),
        object_id=str(instance.pk),
        object_repr=str(instance)[:255],
        changes=_mask_changes(_model_label(instance), changes or {}),
        ip_address=ctx.get("ip_address"),
        user_agent=ctx.get("user_agent", "")[:512],
    )


def diff_instance(old, new):
    if not old:
        return {}
    changes = {}
    for field in new._meta.fields:
        name = field.name
        if name in {"updated_at", "created_at"}:
            continue
        old_val = getattr(old, name)
        new_val = getattr(new, name)
        if old_val != new_val:
            changes[name] = {"old": str(old_val), "new": str(new_val)}
    return changes
