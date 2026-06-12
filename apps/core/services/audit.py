import hashlib
import json

from django.utils import timezone

from apps.core.context import get_audit_context
from apps.core.models import AuditLog


SENSITIVE_FIELDS = {
    "employee": {
        "nik",
        "npwp",
        "bank_account_number",
        "bank_account_name",
        "base_salary",
        "allowance_transport",
        "allowance_meal",
        "allowance_position",
        "bpjs_kesehatan_number",
        "bpjs_ketenagakerjaan_number",
    },
    "user": {"password"},
    "payslip": {"gross_amount", "net_amount", "deduction_amount"},
}


def _model_label(instance):
    return instance._meta.label_lower


def _tenant_id_for(instance) -> int | None:
    if hasattr(instance, "tenant_id") and instance.tenant_id:
        return instance.tenant_id
    if hasattr(instance, "employee_id") and instance.employee_id:
        if hasattr(instance, "_state") and getattr(instance, "employee", None):
            emp = instance.employee
            if hasattr(emp, "tenant_id"):
                return emp.tenant_id
        from apps.employees.models import Employee

        return (
            Employee.objects.filter(pk=instance.employee_id)
            .values_list("tenant_id", flat=True)
            .first()
        )
    if hasattr(instance, "payroll_run_id") and instance.payroll_run_id:
        from apps.payroll.models import PayrollRun

        return (
            PayrollRun.objects.filter(pk=instance.payroll_run_id)
            .values_list("tenant_id", flat=True)
            .first()
        )
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


def _integrity_hash(
    *,
    tenant_id,
    user_id,
    action,
    model_name,
    object_id,
    object_repr,
    changes,
    ip_address,
    user_agent,
    created_at,
) -> str:
    payload = json.dumps(
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "action": action,
            "model_name": model_name,
            "object_id": object_id,
            "object_repr": object_repr,
            "changes": changes,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": created_at.replace(microsecond=0).isoformat(),
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def log_audit(action, instance, *, changes=None):
    tenant_id = _tenant_id_for(instance)
    if not tenant_id:
        return

    ctx = get_audit_context()
    model_name = _model_label(instance)
    masked_changes = _mask_changes(model_name, changes or {})
    created_at = timezone.now()
    user = ctx.get("user")
    ip_address = ctx.get("ip_address")
    user_agent = (ctx.get("user_agent") or "")[:512]

    integrity_hash = _integrity_hash(
        tenant_id=tenant_id,
        user_id=user.pk if user else None,
        action=action,
        model_name=model_name,
        object_id=str(instance.pk),
        object_repr=str(instance)[:255],
        changes=masked_changes,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=created_at,
    )

    AuditLog.objects.create(
        tenant_id=tenant_id,
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(instance.pk),
        object_repr=str(instance)[:255],
        changes=masked_changes,
        ip_address=ip_address,
        user_agent=user_agent,
        integrity_hash=integrity_hash,
        created_at=created_at,
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


def verify_integrity(log: AuditLog) -> bool:
    if not log.integrity_hash:
        return False
    expected = _integrity_hash(
        tenant_id=log.tenant_id,
        user_id=log.user_id,
        action=log.action,
        model_name=log.model_name,
        object_id=log.object_id,
        object_repr=log.object_repr,
        changes=log.changes,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        created_at=log.created_at.replace(microsecond=0),
    )
    return expected == log.integrity_hash
