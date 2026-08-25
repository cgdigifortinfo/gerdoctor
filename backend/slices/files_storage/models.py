"""Immutable values for file metadata and downloads."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FilePrincipal:
    id: str
    role: str
    partner_id: str | None = None


@dataclass(frozen=True, slots=True)
class StoredFile:
    id: str
    user_id: str | None
    storage_path: str
    original_filename: str
    content_type: str
    size: int
    is_deleted: bool = False


@dataclass(frozen=True, slots=True)
class UploadedFile:
    id: str
    filename: str
    path: str


@dataclass(frozen=True, slots=True)
class FileDownload:
    data: bytes
    content_type: str
