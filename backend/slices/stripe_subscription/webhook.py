"""Stripe webhook application service and Mongo persistence adapter."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Protocol, cast

from infrastructure.mongo_ids import object_id_or_none
from infrastructure.stripe_webhook import verified_stripe_event
from slices.stripe_subscription.domain import subscription_webhook_action


class StripeWebhookRepository(Protocol):
    async def settings(self) -> dict[str, Any]: ...
    async def update_charge(self, charge_id: str, fields: Mapping[str, Any]) -> None: ...
    async def update_partner(
        self, partner_id: str | None, customer_id: str | None, fields: Mapping[str, Any],
    ) -> dict[str, Any] | None: ...


class MongoStripeWebhookRepository:
    def __init__(self, database: Any) -> None:
        self._database = database

    async def settings(self) -> dict[str, Any]:
        return cast(dict[str, Any], await self._database.site_settings.find_one({"_key": "global"}) or {})

    async def update_charge(self, charge_id: str, fields: Mapping[str, Any]) -> None:
        await self._database.partner_usage_charges.update_one(
            {"id": charge_id}, {"$set": dict(fields)},
        )

    async def update_partner(
        self, partner_id: str | None, customer_id: str | None, fields: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        object_id = object_id_or_none(partner_id) if partner_id else None
        query: dict[str, Any] = (
            {"_id": object_id} if object_id is not None
            else {"stripe_customer_id": customer_id}
        )
        await self._database.partners.update_one(query, {"$set": dict(fields)})
        return cast(dict[str, Any] | None, await self._database.partners.find_one(query))


UsageSync = Callable[[dict[str, Any]], Awaitable[int]]


class StripeWebhookService:
    def __init__(
        self, repository: StripeWebhookRepository, sync_usage: UsageSync,
        now_iso: Callable[[], str], now_timestamp: Callable[[], float],
    ) -> None:
        self._repository = repository
        self._sync_usage = sync_usage
        self._now_iso = now_iso
        self._now_timestamp = now_timestamp

    async def handle(self, body: bytes, signature: str) -> None:
        settings = await self._repository.settings()
        prefix = "test" if settings.get("stripe_sandbox_mode", True) else "live"
        secret = str(settings.get(f"stripe_{prefix}_webhook_secret", ""))
        event = verified_stripe_event(body, signature, secret, self._now_timestamp)
        obj = event.get("data", {}).get("object", {})
        event_type = str(event.get("type", ""))
        if event_type in {"invoice.created", "invoice.finalized", "invoice.paid"}:
            await self._update_invoice_charges(event_type, obj)
        action = subscription_webhook_action(event_type, obj, self._now_iso())
        if action is None:
            return
        metadata = obj.get("metadata") or {}
        partner_id = metadata.get("partner_id") or obj.get("client_reference_id")
        partner = await self._repository.update_partner(
            partner_id, obj.get("customer"), action.fields,
        )
        if action.sync_pending_usage and partner is not None:
            await self._sync_usage(partner)

    async def _update_invoice_charges(
        self, event_type: str, obj: Mapping[str, Any],
    ) -> None:
        for line in (obj.get("lines") or {}).get("data", []):
            metadata = line.get("metadata") or {}
            charge_id = metadata.get("usage_charge_id")
            if not charge_id:
                parent = line.get("parent") or {}
                metadata = (parent.get("invoice_item_details") or {}).get("metadata") or metadata
                charge_id = metadata.get("usage_charge_id")
            if not charge_id:
                continue
            fields: dict[str, Any] = {
                "stripe_invoice_id": obj.get("id"), "invoice_number": obj.get("number"),
            }
            if event_type == "invoice.paid":
                fields.update({"status": "billed", "billed_at": self._now_iso()})
            await self._repository.update_charge(str(charge_id), fields)
