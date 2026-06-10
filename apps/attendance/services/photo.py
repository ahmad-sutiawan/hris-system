import base64
import binascii
import uuid

from django.core.files.base import ContentFile

MAX_PHOTO_BYTES = 5 * 1024 * 1024


class PhotoError(Exception):
    pass


def decode_selfie(data_url: str) -> ContentFile:
    """Decode a base64 data URL from the browser camera capture."""
    if not data_url or not isinstance(data_url, str):
        raise PhotoError("Foto selfie wajib diambil dari kamera.")

    if not data_url.startswith("data:image"):
        raise PhotoError("Format foto tidak valid.")

    try:
        _header, encoded = data_url.split(",", 1)
    except ValueError as exc:
        raise PhotoError("Format foto tidak valid.") from exc

    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise PhotoError("Foto tidak dapat dibaca.") from exc

    if len(raw) < 1024:
        raise PhotoError("Foto terlalu kecil. Ambil ulang dari kamera.")
    if len(raw) > MAX_PHOTO_BYTES:
        raise PhotoError("Foto terlalu besar (maks 5 MB).")

    return ContentFile(raw, name=f"punch-{uuid.uuid4().hex}.jpg")
