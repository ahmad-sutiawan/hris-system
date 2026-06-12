import base64
import hashlib

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

ENC_PREFIX = "enc:v1:"


def _fernet():
    from cryptography.fernet import Fernet

    raw = getattr(settings, "HRIS_FIELD_ENCRYPTION_KEY", "") or settings.SECRET_KEY
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_value(plain: str) -> str:
    if plain is None or plain == "":
        return ""
    if str(plain).startswith(ENC_PREFIX):
        return str(plain)
    token = _fernet().encrypt(str(plain).encode("utf-8")).decode("utf-8")
    return f"{ENC_PREFIX}{token}"


def decrypt_value(stored: str) -> str:
    if stored is None or stored == "":
        return ""
    if not str(stored).startswith(ENC_PREFIX):
        return str(stored)
    token = str(stored)[len(ENC_PREFIX) :]
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        raise ImproperlyConfigured("Gagal dekripsi field — periksa HRIS_FIELD_ENCRYPTION_KEY.") from exc
