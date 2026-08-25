"""Administrative FastAPI routes for domain events."""
from __future__ import annotations
from collections.abc import Awaitable, Callable, Mapping
from typing import Any
from fastapi import APIRouter, HTTPException, Query, Request
from slices.event_system.service import EventSystemService
from slices.event_system.web import EventConfigUpdate, event_system_http_error

Actor = Mapping[str, Any]
Guard = Callable[[str], Callable[[Request], Awaitable[Actor]]]
Audit = Callable[[object, object, str, str, object, Mapping[str, Any]], Awaitable[None]]
Retry = Callable[[str], Awaitable[dict[str, Any]]]

def build_event_system_router(service: EventSystemService, require_role: Guard,
                              audit: Audit, retry: Retry) -> APIRouter:
    router = APIRouter(prefix="/admin", tags=["admin"])
    @router.get("/event-configs")
    async def configs(request: Request) -> list[dict[str, Any]]:
        await require_role("admin")(request); return await service.configs()
    @router.put("/event-configs/{event_type}")
    async def update_config(event_type: str, payload: EventConfigUpdate, request: Request) -> dict[str, Any]:
        actor = await require_role("admin")(request); update = payload.model_dump(exclude_none=True)
        try: updated = await service.update_config(event_type, update)
        except Exception as error: raise event_system_http_error(error)
        await audit(str(actor.get("_id") or ""), actor.get("email", ""), "event_config_update",
                    "event_config", event_type, {"fields": [*update, "updated_at"]})
        return updated
    @router.get("/events")
    async def events(request: Request, limit: int = Query(default=100, ge=0, le=1000),
                     skip: int = Query(default=0, ge=0), event_type: str = "", status: str = "") -> dict[str, Any]:
        await require_role("admin")(request)
        return (await service.events(event_type, status, limit, skip)).to_document()
    @router.post("/events/{event_id}/retry")
    async def retry_event(event_id: str, request: Request) -> dict[str, Any]:
        actor = await require_role("admin")(request)
        try: event = await retry(event_id)
        except ValueError: raise HTTPException(404, "Event not found")
        await audit(str(actor.get("_id") or ""), actor.get("email", ""), "event_retry", "domain_event", event_id, {})
        return event
    return router
