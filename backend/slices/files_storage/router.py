"""FastAPI upload and download routes for managed files."""
from __future__ import annotations
from collections.abc import Awaitable, Callable, Mapping
from typing import Any
from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from infrastructure.local_object_storage import LocalStorageError
from slices.files_storage.domain import FileRuleError
from slices.files_storage.models import FilePrincipal
from slices.files_storage.service import FilesStorageError, FilesStorageService
from slices.files_storage.web import files_storage_http_error, uploaded_file_payload

CurrentUser = Callable[[Request], Awaitable[Mapping[str, Any]]]
Principal = Callable[[Mapping[str, Any]], FilePrincipal]
def build_files_router(service: FilesStorageService, current_user: CurrentUser, principal: Principal,
                       new_id: Callable[[], str], now: Callable[[], str], max_bytes: int) -> APIRouter:
    router = APIRouter(prefix="/files", tags=["files"])
    @router.post("/upload")
    async def upload(request: Request, file: UploadFile = File(...)) -> dict[str, Any]:
        actor = await current_user(request); data = await file.read(max_bytes + 1)
        try: uploaded = await service.upload(principal(actor), new_id(), file.filename, file.content_type, data, now())
        except (FileRuleError, FilesStorageError, LocalStorageError) as error: raise files_storage_http_error(error)
        return uploaded_file_payload(uploaded)
    @router.get("/{file_id}")
    async def download(file_id: str, request: Request, auth: str | None = Query(None)) -> Response:
        if auth:
            request.scope["headers"] = list(request.scope.get("headers", [])) + [(b"authorization", f"Bearer {auth}".encode())]
        try: actor = await current_user(request)
        except HTTPException: raise HTTPException(401, "Not authenticated")
        try: result = await service.download(principal(actor), file_id)
        except (FileRuleError, FilesStorageError, LocalStorageError) as error: raise files_storage_http_error(error)
        return Response(content=result.data, media_type=result.content_type)
    return router
