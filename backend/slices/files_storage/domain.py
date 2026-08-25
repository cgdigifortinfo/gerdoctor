"""Pure upload validation, naming and immediate access rules."""
from __future__ import annotations

from pathlib import PurePath

from slices.files_storage.models import FilePrincipal, StoredFile

APP_STORAGE_PREFIX = "gerdoctor"
ALLOWED_UPLOAD_EXTENSIONS = frozenset({
    "pdf", "png", "jpg", "jpeg", "webp", "gif", "doc", "docx", "xls",
    "xlsx", "csv", "txt", "zip",
})
BLOCKED_UPLOAD_CONTENT_TYPES = frozenset({
    "text/html", "application/xhtml+xml", "image/svg+xml",
    "application/javascript", "text/javascript",
})


class FileRuleError(ValueError): pass
class UnsupportedFileType(FileRuleError): pass
class FileTooLarge(FileRuleError): pass


def safe_upload_extension(filename: str) -> str:
    extension = PurePath(filename).suffix.removeprefix(".").lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise UnsupportedFileType
    return extension


def validate_upload(content_type: str, size: int, maximum_size: int) -> None:
    if content_type.lower() in BLOCKED_UPLOAD_CONTENT_TYPES:
        raise UnsupportedFileType
    if size > maximum_size:
        raise FileTooLarge


def original_filename(filename: str | None, file_id: str, extension: str) -> str:
    return PurePath(filename or f"{file_id}.{extension}").name


def storage_path(user_id: str, file_id: str, extension: str) -> str:
    return f"{APP_STORAGE_PREFIX}/uploads/{user_id}/{file_id}.{extension}"


def immediate_access(principal: FilePrincipal, stored_file: StoredFile) -> bool | None:
    if not stored_file.user_id:
        return False
    if principal.role == "admin" or principal.id == stored_file.user_id:
        return True
    if principal.role not in {"user", "partner"}:
        return False
    if principal.role == "partner" and not principal.partner_id:
        return False
    return None
