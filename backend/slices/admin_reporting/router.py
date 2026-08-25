"""FastAPI boundary for administrative reports."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from fastapi import APIRouter, Request

from slices.admin_reporting.service import AdminReportingService


Guard = Callable[[str], Callable[[Request], Awaitable[Mapping[str, Any]]]]


def build_admin_reporting_router(
    service: AdminReportingService, require_role: Guard,
) -> APIRouter:
    router = APIRouter(prefix="/admin", tags=["admin"])

    @router.get("/analytics")
    async def analytics(request: Request) -> dict[str, Any]:
        await require_role("admin")(request)
        return await service.analytics()

    @router.get("/billing")
    async def billing(request: Request) -> dict[str, Any]:
        await require_role("admin")(request)
        return await service.billing()

    return router
