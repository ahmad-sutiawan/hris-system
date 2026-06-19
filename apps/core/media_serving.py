"""Protected media access — session auth, JWT, or signed URLs."""

from __future__ import annotations

import mimetypes
from pathlib import PurePosixPath
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponseForbidden

User = get_user_model()
_signer = TimestampSigner(salt="hris-protected-media")


def _media_ttl() -> int:
    return int(getattr(settings, "HRIS_MEDIA_URL_TTL_SECONDS", 3600))


def media_protection_enabled() -> bool:
    return bool(getattr(settings, "HRIS_MEDIA_PROTECTED", not settings.DEBUG))


def sign_media_path(relative_path: str) -> str:
    """Return relative media URL with HMAC timestamp signature."""
    relative_path = relative_path.lstrip("/")
    token = _signer.sign(relative_path)
    return f"{settings.MEDIA_URL}{relative_path}?sig={quote(token)}"


def build_media_url(relative_path: str | None, *, request=None) -> str | None:
    if not relative_path:
        return None
    path = relative_path.lstrip("/")
    if media_protection_enabled():
        url = sign_media_path(path)
    else:
        url = f"{settings.MEDIA_URL}{path}"
    site = getattr(settings, "HRIS_SITE_URL", "").rstrip("/")
    if site:
        return f"{site}{url}" if url.startswith("/") else f"{site}/{url}"
    if request is not None:
        return request.build_absolute_uri(url)
    return url


def verify_media_signature(relative_path: str, token: str) -> bool:
    try:
        unsigned = _signer.unsign(token, max_age=_media_ttl())
    except (BadSignature, SignatureExpired):
        return False
    return unsigned == relative_path.lstrip("/")


def _authenticate_jwt(request):
    from rest_framework_simplejwt.authentication import JWTAuthentication

    auth = JWTAuthentication()
    result = auth.authenticate(request)
    if result:
        request.user = result[0]
        return True
    return False


def _media_in_tenant(tenant_id: int, path: str) -> bool:
    if path.startswith("attendance/"):
        from apps.attendance.models import AttendancePunch, AttendanceRecord

        return (
            AttendanceRecord.objects.filter(tenant_id=tenant_id).filter(
                Q(check_in_photo=path) | Q(check_out_photo=path)
            ).exists()
            or AttendancePunch.objects.filter(tenant_id=tenant_id, photo=path).exists()
        )
    if path.startswith("payslips/"):
        from apps.payroll.models import Payslip

        return Payslip.objects.filter(tenant_id=tenant_id, pdf_file=path).exists()
    if path.startswith("employee_photos/"):
        from apps.employees.models import Employee

        return Employee.objects.filter(tenant_id=tenant_id, photo=path).exists()
    if path.startswith("employee_documents/"):
        from apps.employees.models import EmployeeDocument

        return EmployeeDocument.objects.filter(tenant_id=tenant_id, file=path).exists()
    return False


def user_can_access_media(user, path: str) -> bool:
    if not user.is_authenticated or not user.tenant_id:
        return False

    path = path.lstrip("/")
    if ".." in PurePosixPath(path).parts:
        return False

    if user.is_admin:
        return _media_in_tenant(user.tenant_id, path)

    profile = getattr(user, "employee_profile", None)

    if user.is_hr:
        if user.plant_id:
            return _media_hr_plant_access(user, path)
        return _media_in_tenant(user.tenant_id, path)

    if path.startswith("attendance/") and profile:
        from apps.attendance.models import AttendancePunch, AttendanceRecord

        return (
            AttendanceRecord.objects.filter(employee=profile).filter(
                Q(check_in_photo=path) | Q(check_out_photo=path)
            ).exists()
            or AttendancePunch.objects.filter(employee=profile, photo=path).exists()
        )

    if path.startswith("payslips/") and profile:
        from apps.payroll.models import Payslip

        return Payslip.objects.filter(employee=profile, pdf_file=path).exists()

    if path.startswith("employee_photos/") and profile:
        return profile.photo.name == path

    if path.startswith("employee_documents/") and profile:
        from apps.employees.models import EmployeeDocument

        return EmployeeDocument.objects.filter(employee=profile, file=path).exists()

    return False


def _media_hr_plant_access(user, path: str) -> bool:
    if path.startswith("attendance/"):
        from apps.attendance.models import AttendancePunch, AttendanceRecord

        return (
            AttendanceRecord.objects.filter(
                tenant_id=user.tenant_id,
                plant_id=user.plant_id,
            ).filter(Q(check_in_photo=path) | Q(check_out_photo=path)).exists()
            or AttendancePunch.objects.filter(
                tenant_id=user.tenant_id,
                employee__plant_id=user.plant_id,
                photo=path,
            ).exists()
        )
    if path.startswith("payslips/"):
        from apps.payroll.models import Payslip

        return Payslip.objects.filter(
            tenant_id=user.tenant_id,
            employee__plant_id=user.plant_id,
            pdf_file=path,
        ).exists()
    if path.startswith("employee_photos/"):
        from apps.employees.models import Employee

        return Employee.objects.filter(
            tenant_id=user.tenant_id,
            plant_id=user.plant_id,
            photo=path,
        ).exists()
    if path.startswith("employee_documents/"):
        from apps.employees.models import EmployeeDocument

        return EmployeeDocument.objects.filter(
            tenant_id=user.tenant_id,
            employee__plant_id=user.plant_id,
            file=path,
        ).exists()
    return False


def serve_protected_media(request, path: str):
    path = path.lstrip("/")
    if ".." in PurePosixPath(path).parts:
        raise Http404

    full_path = settings.MEDIA_ROOT / path
    if not full_path.is_file():
        raise Http404

    sig = request.GET.get("sig")
    if sig and verify_media_signature(path, sig):
        return _file_response(full_path, path)

    if not request.user.is_authenticated:
        _authenticate_jwt(request)

    if request.user.is_authenticated and user_can_access_media(request.user, path):
        return _file_response(full_path, path)

    return HttpResponseForbidden("Akses media ditolak.")


def _file_response(full_path, path: str):
    content_type, _ = mimetypes.guess_type(path)
    return FileResponse(full_path.open("rb"), content_type=content_type or "application/octet-stream")
