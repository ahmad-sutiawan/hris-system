"""Employee profile photo helpers — URL building and loss-aware compression."""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image, ImageOps

from apps.core.media_serving import build_media_url

MAX_DIMENSION = 512
WEBP_QUALITY = 85
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


def employee_photo_url(employee, *, request=None) -> str | None:
    if not employee:
        return None
    photo = getattr(employee, "photo", None)
    if not photo or not photo.name:
        return None
    return build_media_url(photo.name, request=request)


def _is_new_upload(photo) -> bool:
    return bool(photo and hasattr(photo, "file") and photo.file is not None)


def _safe_stem(employee) -> str:
    raw = (getattr(employee, "employee_id", None) or "photo").strip()
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw).strip("-").lower()
    return slug or "photo"


def compress_employee_photo(employee) -> None:
    """Resize and re-encode profile photos to WebP for fast avatar loading."""
    photo = employee.photo
    if not photo or not photo.name:
        return

    try:
        with photo.open("rb") as handle:
            image = Image.open(handle)
            image.load()
    except Exception:
        return

    if hasattr(photo, "size") and photo.size and photo.size > MAX_UPLOAD_BYTES and not _is_new_upload(photo):
        return

    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode == "P":
            image = image.convert("RGBA")
        alpha = image.split()[-1] if "A" in image.mode else None
        background.paste(image, mask=alpha)
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")

    image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

    buffer = BytesIO()
    image.save(buffer, format="WEBP", quality=WEBP_QUALITY, method=4)
    payload = buffer.getvalue()
    if not payload:
        return

    now = timezone.localdate()
    stem = Path(photo.name).stem if photo.name else _safe_stem(employee)
    if stem in {"", "photo"}:
        stem = _safe_stem(employee)
    new_name = f"employee_photos/{now:%Y/%m}/{stem}.webp"
    employee.photo.save(new_name, ContentFile(payload), save=False)


def maybe_compress_employee_photo(employee, *, previous_name: str = "") -> None:
    """Compress only when the uploaded file changed."""
    photo = employee.photo
    if not photo or not photo.name:
        return
    if _is_new_upload(photo) or photo.name != previous_name:
        compress_employee_photo(employee)
