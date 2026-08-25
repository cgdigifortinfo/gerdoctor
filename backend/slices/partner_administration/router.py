"""FastAPI boundary for administrative partner management."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from fastapi import APIRouter, Request

from slices.partner_administration.domain import partner_update_plan
from slices.partner_administration.listing import PartnerAdministrationListingService
from slices.partner_administration.service import (
    PartnerAdministrationError,
    PartnerAdministrationService,
)
from slices.partner_administration.web import (
    PartnerCreate,
    PartnerUpdate,
    partner_administration_http_error,
)


Actor = Mapping[str, Any]
Guard = Callable[[str], Callable[[Request], Awaitable[Actor]]]
Audit = Callable[[object, object, str, str, object, Mapping[str, Any]], Awaitable[None]]
GroupId = Callable[[str], Awaitable[str | None]]
Timestamp = Callable[[], str]
UsageSync = Callable[[dict[str, Any]], Awaitable[int]]


def build_partner_administration_router(
    service: PartnerAdministrationService,
    listing: PartnerAdministrationListingService,
    require_role: Guard,
    default_group_id: GroupId,
    audit: Audit,
    now_iso: Timestamp,
    sync_pending_usage: UsageSync,
) -> APIRouter:
    router = APIRouter(prefix="/admin/partners", tags=["admin"])

    @router.get("")
    async def partners(request: Request) -> list[dict[str, Any]]:
        await require_role("admin")(request)
        return await listing.list()

    @router.post("")
    async def create(data: PartnerCreate, request: Request) -> dict[str, str]:
        actor = await require_role("admin")(request)
        partner_id = await service.create(data.model_dump(), now_iso())
        await audit(actor["_id"], actor["email"], "partner_create", "partner", partner_id,
                    {"name": data.name})
        return {"id": partner_id, "message": "Partner created"}

    @router.put("/{partner_id}")
    async def update(
        partner_id: str, data: PartnerUpdate, request: Request,
    ) -> dict[str, str]:
        actor = await require_role("admin")(request)
        try:
            updated = await service.update(partner_id, data.model_dump(), now_iso())
        except PartnerAdministrationError as error:
            raise partner_administration_http_error(error)
        if updated.get("stripe_customer_id") and updated.get("stripe_subscription_id"):
            await sync_pending_usage(updated)
        changed = list(partner_update_plan(data.model_dump(), updated["updated_at"]).fields)
        await audit(actor["_id"], actor["email"], "partner_update", "partner", partner_id,
                    {"fields_changed": changed})
        return {"message": "Partner updated"}

    @router.delete("/{partner_id}")
    async def delete(partner_id: str, request: Request) -> dict[str, str]:
        actor = await require_role("admin")(request)
        try:
            deletion = await service.delete(partner_id, await default_group_id("user"))
        except PartnerAdministrationError as error:
            raise partner_administration_http_error(error)
        await audit(actor["_id"], actor["email"], "partner_delete", "partner", partner_id,
                    {"name": deletion.partner_name})
        return {"message": "Partner deleted"}

    @router.put("/{partner_id}/link-user")
    async def link(partner_id: str, user_id: str, request: Request) -> dict[str, str]:
        await require_role("admin")(request)
        try:
            name = await service.link_user(
                partner_id, user_id, await default_group_id("user"),
                await default_group_id("partner"),
            )
        except PartnerAdministrationError as error:
            raise partner_administration_http_error(error)
        return {"message": "Partner linked to user", "user_name": name}

    @router.put("/{partner_id}/unlink-user")
    async def unlink(partner_id: str, request: Request) -> dict[str, str]:
        await require_role("admin")(request)
        try:
            await service.unlink_user(partner_id, await default_group_id("user"))
        except PartnerAdministrationError as error:
            raise partner_administration_http_error(error)
        return {"message": "Partner unlinked from user"}

    return router
