"""FastAPI routes for CMS content and public settings."""
from __future__ import annotations
from collections.abc import Awaitable, Callable, Mapping
from typing import Any
from fastapi import APIRouter, Request
from slices.cms_public_settings.service import CmsPublicSettingsService
from slices.cms_public_settings.web import CMSContentUpdate, SiteSettingsUpdate

Actor = Mapping[str, Any]
Guard = Callable[[str], Callable[[Request], Awaitable[Actor]]]
Audit = Callable[[object, object, str, str, object, Mapping[str, Any]], Awaitable[None]]
StripeStatus = Callable[[], Awaitable[Mapping[str, Any]]]

def build_cms_settings_routers(service: CmsPublicSettingsService, require_role: Guard,
                               require_permission: Guard, audit: Audit,
                               stripe_status: StripeStatus) -> tuple[APIRouter, APIRouter, APIRouter]:
    cms = APIRouter(prefix="/cms", tags=["cms"]); admin = APIRouter(prefix="/admin", tags=["admin"])
    public = APIRouter(tags=["settings"])
    @cms.get("")
    async def all_content() -> dict[str, dict[str, dict[str, Any]]]: return await service.all_content()
    @cms.get("/{section}")
    async def content(section: str) -> dict[str, dict[str, Any]]: return await service.content(section)
    @cms.put("/{section}")
    async def update_content(section: str, data: CMSContentUpdate, request: Request) -> dict[str, str]:
        actor = await require_permission("cms.manage")(request)
        await service.update_content(section, data.content, data.translations, data.translations is not None)
        await audit(actor["_id"], actor["email"], "cms_update", "cms", section, {"section": section})
        return {"message": "Content updated"}
    @admin.get("/settings")
    async def admin_settings(request: Request) -> dict[str, Any]:
        await require_role("admin")(request); return await service.admin_settings(await stripe_status())
    @admin.put("/settings")
    async def update_settings(data: SiteSettingsUpdate, request: Request) -> dict[str, str]:
        actor = await require_role("admin")(request); fields = await service.update_settings(data.model_dump())
        await audit(actor["_id"], actor["email"], "settings_update", "settings", "", {"fields": fields})
        return {"message": "Settings updated"}
    @public.get("/settings/public")
    async def public_settings() -> dict[str, Any]: return await service.public_settings(await stripe_status())
    return cms, admin, public
