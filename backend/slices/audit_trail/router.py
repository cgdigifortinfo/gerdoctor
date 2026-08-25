"""Administrative FastAPI route for audit history."""
from __future__ import annotations
from collections.abc import Awaitable, Callable, Mapping
from typing import Any
from fastapi import APIRouter, Request
from slices.audit_trail.service import AuditTrailService

Guard = Callable[[str], Callable[[Request], Awaitable[Mapping[str, Any]]]]
def build_audit_trail_router(service: AuditTrailService, require_role: Guard) -> APIRouter:
    router = APIRouter(prefix="/admin", tags=["admin"])
    @router.get("/audit-log")
    async def audit_log(request: Request, limit: int = 100, skip: int = 0, action: str = "",
                        date_from: str = "", date_to: str = "") -> dict[str, Any]:
        await require_role("admin")(request)
        return (await service.page(limit, skip, action, date_from, date_to)).to_document()
    return router
