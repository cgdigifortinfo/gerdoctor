"""Application service for upload, download and historical protection."""
from __future__ import annotations

from slices.files_storage.domain import (
    immediate_access, original_filename, safe_upload_extension, storage_path,
    validate_upload,
)
from slices.files_storage.models import FileDownload, FilePrincipal, StoredFile, UploadedFile
from slices.files_storage.ports import FilesRepository, ObjectStorage


class FilesStorageError(ValueError): pass
class UnknownFile(FilesStorageError): pass
class FileAccessDenied(FilesStorageError): pass


class FilesStorageService:
    def __init__(self, repository: FilesRepository, storage: ObjectStorage,
                 maximum_upload_size: int) -> None:
        self._repository = repository
        self._storage = storage
        self._maximum_upload_size = maximum_upload_size

    def initialize(self) -> str:
        return self._storage.initialize()

    async def upload(self, principal: FilePrincipal, file_id: str, filename: str | None,
                     content_type: str | None, data: bytes, created_at: str) -> UploadedFile:
        extension = safe_upload_extension(filename or "")
        media_type = content_type or "application/octet-stream"
        validate_upload(media_type, len(data), self._maximum_upload_size)
        path = storage_path(principal.id, file_id, extension)
        size = self._storage.put(path, data, media_type)
        name = original_filename(filename, file_id, extension)
        await self._repository.insert(StoredFile(
            file_id, principal.id, path, name, media_type, size,
        ), created_at)
        return UploadedFile(file_id, name, path)

    async def download(self, principal: FilePrincipal, file_id: str) -> FileDownload:
        stored_file = await self._repository.find_active(file_id)
        if stored_file is None:
            raise UnknownFile(file_id)
        access = immediate_access(principal, stored_file)
        if access is None and principal.role == "user":
            access = await self._repository.user_references_file(principal.id, file_id)
        elif access is None and principal.partner_id:
            access = await self._repository.partner_links_user(principal.partner_id, stored_file.user_id or "")
            if not access:
                access = await self._repository.partner_submission_exists(principal.partner_id, stored_file.user_id or "")
        if not access:
            raise FileAccessDenied(file_id)
        data, fallback_content_type = self._storage.get(stored_file.storage_path)
        return FileDownload(data, stored_file.content_type or fallback_content_type)

    async def protect_owner_files(self, user_id: str, deleted_at: str) -> None:
        await self._repository.protect_owner_files(user_id, deleted_at)
