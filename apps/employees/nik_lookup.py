import hashlib


def compute_nik_lookup(nik: str) -> str:
    """Hash deterministik NIK untuk lookup login (NIK tetap terenkripsi di DB)."""
    normalized = (nik or "").strip()
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
