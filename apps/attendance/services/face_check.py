"""Basic selfie validation — extensible for face recognition."""

from __future__ import annotations

from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile


class FaceCheckError(Exception):
    pass


def _region_luminance_stats(img, box: tuple[int, int, int, int]) -> tuple[float, float]:
    from PIL import ImageStat

    region = img.crop(box).convert("L")
    stat = ImageStat.Stat(region)
    return float(stat.mean[0]), float(stat.stddev[0])


def _detect_hat_or_mask(img) -> None:
    """POC heuristic: uniform upper band (topi) or flat center band (masker)."""
    w, h = img.size
    if w < 200 or h < 200:
        return

    top = _region_luminance_stats(img, (0, 0, w, max(1, int(h * 0.35))))
    mid = _region_luminance_stats(img, (0, h // 3, w, (2 * h) // 3))
    center = _region_luminance_stats(
        img,
        (w // 4, h // 3, (3 * w) // 4, (2 * h) // 3),
    )

    _, top_std = top
    _, mid_std = mid
    _, center_std = center

    if top_std <= 6 and mid_std >= 14 and top_std < mid_std * 0.5:
        raise FaceCheckError("Lepas topi atau penutup kepala sebelum absen.")

    if center_std <= 8 and mid_std >= 14 and center_std < mid_std * 0.45:
        raise FaceCheckError("Lepas masker sebelum absen.")


def _histogram_similarity(left, right) -> float:
    from PIL import Image

    size = (64, 64)
    a = left.convert("RGB").resize(size)
    b = right.convert("RGB").resize(size)
    hist_a = a.histogram()
    hist_b = b.histogram()
    if not hist_a or not hist_b:
        return 0.0

    dot = sum(x * y for x, y in zip(hist_a, hist_b))
    norm_a = sum(x * x for x in hist_a) ** 0.5
    norm_b = sum(y * y for y in hist_b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _match_profile_photo(photo: ContentFile, employee) -> None:
    if not getattr(settings, "FACE_PROFILE_MATCH_ENABLED", False):
        return
    if not employee or not getattr(employee, "photo", None):
        return
    if not employee.photo:
        return

    threshold = float(getattr(settings, "FACE_PROFILE_MATCH_THRESHOLD", 0.35))
    from PIL import Image

    selfie = Image.open(BytesIO(photo.read()))
    photo.seek(0)
    with employee.photo.open("rb") as profile_file:
        profile = Image.open(profile_file)
        score = _histogram_similarity(selfie, profile)
    if score < threshold:
        raise FaceCheckError("Wajah tidak cocok dengan foto profil karyawan.")


def validate_selfie_face(photo: ContentFile, *, employee=None) -> None:
    """
    Quality gate for punch selfies.
    Optional profile match when FACE_PROFILE_MATCH_ENABLED=True.
    """
    if not photo:
        raise FaceCheckError("Foto selfie wajib.")

    data = photo.read()
    photo.seek(0)
    if len(data) < 1024:
        raise FaceCheckError("Foto terlalu kecil atau tidak valid.")

    try:
        from PIL import Image

        img = Image.open(BytesIO(data))
        img.verify()
        photo.seek(0)
        img = Image.open(BytesIO(data))
        w, h = img.size
        if w < 200 or h < 200:
            raise FaceCheckError("Resolusi foto terlalu rendah. Dekatkan wajah ke kamera.")
        _detect_hat_or_mask(img)
        _match_profile_photo(photo, employee)
    except FaceCheckError:
        raise
    except Exception as exc:
        raise FaceCheckError("Format foto tidak valid.") from exc

    photo.seek(0)
