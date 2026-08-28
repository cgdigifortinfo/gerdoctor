"""Tests for partner-logo validation and encoding."""
from __future__ import annotations

import pytest

from slices.partner_workspace.logo import (
    InvalidPartnerLogo, MAX_PARTNER_LOGO_BYTES, PartnerLogoTooLarge,
    _has_valid_signature, partner_logo_data_url,
)


@pytest.mark.parametrize(("filename", "content_type", "content", "prefix"), [
    ("logo.png", "image/png", b"\x89PNG\r\n\x1a\nbody", "data:image/png;base64,"),
    ("logo.JPG", "image/jpeg", b"\xff\xd8\xffbody", "data:image/jpeg;base64,"),
    ("logo.webp", "image/webp", b"RIFF0000WEBPbody", "data:image/webp;base64,"),
])
def test_partner_logo_accepts_supported_images(filename, content_type, content, prefix) -> None:
    expected = prefix + __import__("base64").b64encode(content).decode("ascii")
    assert partner_logo_data_url(filename, content_type, content) == expected


@pytest.mark.parametrize(("content_type", "content", "expected"), [
    ("image/png", b"\x89PNG\r\n\x1a\n", True),
    ("image/png", b"\x89PNG\r\n\x1aX", False),
    ("image/jpeg", b"\xff\xd8\xff", True),
    ("image/jpeg", b"\xff\xd8X", False),
    ("image/webp", b"RIFF0000WEBP", True),
    ("image/webp", b"RIFF0000WEBX", False),
    ("image/webp", b"RIFFWEBP", False),
    ("image/gif", b"GIF89a", False),
])
def test_partner_logo_checks_exact_file_signatures(content_type, content, expected) -> None:
    assert _has_valid_signature(content_type, content) is expected


@pytest.mark.parametrize(("filename", "content_type", "content"), [
    ("logo.png", "image/png", b""),
    ("logo.svg", "image/svg+xml", b"<svg/>"),
    ("logo.jpg", "image/png", b"\x89PNG\r\n\x1a\nbody"),
    ("logo.png", "image/png", b"not a png"),
    ("logo.jpg", "image/jpeg", b"not a jpeg"),
    ("logo.webp", "image/webp", b"not a webp"),
])
def test_partner_logo_rejects_empty_mismatched_and_invalid_images(
    filename, content_type, content,
) -> None:
    expected_message = (
        "Logo file is empty" if not content else
        "File content does not match the selected image type"
        if filename.rsplit(".", 1)[-1].lower() in {"png", "jpg", "jpeg", "webp"}
        and content_type in {"image/png", "image/jpeg", "image/webp"}
        and ((filename.lower().endswith(".png") and content_type == "image/png")
             or (filename.lower().endswith((".jpg", ".jpeg")) and content_type == "image/jpeg")
             or (filename.lower().endswith(".webp") and content_type == "image/webp"))
        else "Logo must be a PNG, JPEG or WebP image"
    )
    with pytest.raises(InvalidPartnerLogo, match=f"^{expected_message}$"):
        partner_logo_data_url(filename, content_type, content)


def test_partner_logo_rejects_files_over_two_megabytes() -> None:
    with pytest.raises(PartnerLogoTooLarge):
        partner_logo_data_url(
            "logo.png", "image/png",
            b"\x89PNG\r\n\x1a\n" + b"x" * MAX_PARTNER_LOGO_BYTES,
        )


def test_partner_logo_accepts_exact_size_limit_and_normalizes_metadata() -> None:
    content = b"\x89PNG\r\n\x1a\n" + b"x" * (MAX_PARTNER_LOGO_BYTES - 8)
    result = partner_logo_data_url("LOGO.PNG", " IMAGE/PNG; charset=binary; version=1 ", content)
    assert result == "data:image/png;base64," + __import__("base64").b64encode(content).decode("ascii")
