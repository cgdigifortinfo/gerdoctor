"""HTTP representations and errors for files and storage."""
from fastapi import HTTPException

from slices.files_storage.domain import FileTooLarge, UnsupportedFileType
from slices.files_storage.models import UploadedFile
from slices.files_storage.service import FileAccessDenied, UnknownFile
from infrastructure.local_object_storage import InvalidStoragePath, StoredObjectNotFound


def uploaded_file_payload(uploaded: UploadedFile) -> dict[str, str]:
    return {"id": uploaded.id, "filename": uploaded.filename, "path": uploaded.path}


def files_storage_http_error(error: Exception) -> HTTPException:
    if isinstance(error, UnsupportedFileType):
        return HTTPException(status_code=400, detail="Unsupported file type")
    if isinstance(error, FileTooLarge):
        return HTTPException(status_code=413, detail="File too large")
    if isinstance(error, UnknownFile):
        return HTTPException(status_code=404, detail="File not found")
    if isinstance(error, FileAccessDenied):
        return HTTPException(status_code=403, detail="Insufficient permissions")
    if isinstance(error, InvalidStoragePath):
        return HTTPException(status_code=400, detail="Invalid storage path")
    if isinstance(error, StoredObjectNotFound):
        return HTTPException(status_code=404, detail="Stored file not found")
    return HTTPException(status_code=400, detail="Invalid file operation")
