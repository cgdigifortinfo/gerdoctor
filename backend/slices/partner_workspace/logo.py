"""Validation and encoding for partner profile logos."""
from __future__ import annotations

import base64
from pathlib import Path


MAX_PARTNER_LOGO_BYTES = 2 * 1024 * 1024
ALLOWED_PARTNER_LOGO_TYPES = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
}


def _has_valid_signature(content_type: str, content: bytes) -> bool:
    if content_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")  # pragma: no mutate - hexadecimal byte casing is equivalent
    if content_type == "image/jpeg":
        return content.startswith(bytes((255, 216, 255)))
    if content_type == "image/webp":
        return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    return False


class InvalidPartnerLogo(ValueError): pass
class PartnerLogoTooLarge(ValueError): pass


def partner_logo_data_url(filename: str, content_type: str, content: bytes) -> str:
    """Return a safe data URL after validating type, extension and size."""
    if not content:
        raise InvalidPartnerLogo("Logo file is empty")
    if len(content) > MAX_PARTNER_LOGO_BYTES:
        raise PartnerLogoTooLarge
    normalized_type = content_type.partition(";")[0].strip().lower()
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_PARTNER_LOGO_TYPES.get(normalized_type, set()):
        raise InvalidPartnerLogo("Logo must be a PNG, JPEG or WebP image")
    if not _has_valid_signature(normalized_type, content):
        raise InvalidPartnerLogo("File content does not match the selected image type")
    encoded = base64.b64encode(content).decode("ascii")  # pragma: no mutate - codec names are case-insensitive
    return f"data:{normalized_type};base64,{encoded}"
