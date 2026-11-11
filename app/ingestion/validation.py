import hashlib
import os
from typing import Tuple
from app.core.config import settings

ALLOWED_EXTENSIONS = {".eml", ".msg", ".mbox", ".csv", ".json"}


def validate_file_upload(filename: str, content: bytes) -> Tuple[bool, str]:
    """
    Validates file extension, size limit, and non-empty content.
    Returns (is_valid, error_message).
    """
    if not filename:
        return False, "Filename cannot be empty."

    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"

    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.UPLOAD_MAX_SIZE_MB:
        return False, f"File size ({size_mb:.2f} MB) exceeds maximum allowed limit of {settings.UPLOAD_MAX_SIZE_MB} MB."

    if len(content) == 0:
        return False, "File is empty."

    return True, ""


def compute_sha256(content: bytes) -> str:
    """Computes SHA-256 hex digest of file or text content."""
    return hashlib.sha256(content).hexdigest()
