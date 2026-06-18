"""Cari file export Talenta di folder media."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.conf import settings

from apps.employees.talenta_mapping import TALENTA_REQUIRED_IMPORT_COLUMNS
from apps.employees.services.import_talenta import _load_rows


def media_root() -> Path:
    return Path(settings.MEDIA_ROOT)


def find_talenta_excel_file(*, media_dir: Path | None = None) -> Path | None:
    root = media_dir or media_root()
    if not root.is_dir():
        return None

    preferred = root / "employee_db.xlsx"
    if preferred.is_file() and is_talenta_export(preferred):
        return preferred

    candidates = sorted(
        root.glob("*.xlsx"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        if is_talenta_export(path):
            return path
    return None


def is_talenta_export(path: Path) -> bool:
    try:
        _load_rows(path.read_bytes())
        return True
    except (ValueError, OSError):
        return False


def read_talenta_excel(path: Path | None = None) -> tuple[Path, bytes]:
    file_path = path or find_talenta_excel_file()
    if not file_path:
        missing = ", ".join(TALENTA_REQUIRED_IMPORT_COLUMNS[:4])
        raise FileNotFoundError(
            f"Tidak ada file export Talenta (.xlsx) di {media_root()}. "
            f"File harus memiliki kolom: {missing}, …"
        )
    content = file_path.read_bytes()
    _load_rows(content)
    return file_path, content
