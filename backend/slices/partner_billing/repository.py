"""MongoDB adapter for partner usage billing."""
from __future__ import annotations

from typing import Any

from pymongo.errors import DuplicateKeyError

from slices.partner_billing.mappers import charge_from_document, settings_from_document
from slices.partner_billing.models import BillingSettings, UsageCharge


class DuplicateUsageCharge(Exception):
    """Raised when the unique partner/user/service ledger key already exists."""


class PartnerBillingRepository:
    def __init__(self, database: Any) -> None:
        self._db = database

    async def global_settings(self) -> BillingSettings:
        document = await self._db.site_settings.find_one({"_key": "global"}) or {}
        return settings_from_document(document)

    async def find_charge(
        self, partner_id: str, user_id: str, service_step_id: str,
    ) -> UsageCharge | None:
        document = await self._db.partner_usage_charges.find_one({
            "partner_id": partner_id,
            "user_id": user_id,
            "service_step_id": service_step_id,
        })
        return charge_from_document(document) if document else None

    async def insert_charge(self, charge: UsageCharge) -> None:
        try:
            await self._db.partner_usage_charges.insert_one(charge.to_document())
        except DuplicateKeyError as exc:
            raise DuplicateUsageCharge from exc

    async def usage_rows(self, partner_id: str) -> list[UsageCharge]:
        rows = await self._db.partner_usage_charges.find(
            {"partner_id": partner_id}, {"_id": 0}
        ).to_list(10000)
        return [charge_from_document(row) for row in rows]

    async def pending_sync_rows(self, partner_id: str) -> list[UsageCharge]:
        rows = await self._db.partner_usage_charges.find({
            "partner_id": partner_id,
            "status": "pending",
            "stripe_invoice_item_id": {"$exists": False},
            "amount": {"$gt": 0},
        }, {"_id": 0}).to_list(10000)
        return [charge_from_document(row) for row in rows]

    async def mark_sync_error(self, charge_id: str, message: str) -> None:
        await self._db.partner_usage_charges.update_one(
            {"id": charge_id}, {"$set": {"sync_error": message}},
        )

    async def mark_queued(self, charge_id: str, item_id: str | None, queued_at: str) -> None:
        await self._db.partner_usage_charges.update_one(
            {"id": charge_id}, {"$set": {
                "status": "queued",
                "stripe_invoice_item_id": item_id,
                "queued_at": queued_at,
                "sync_error": "",
            }},
        )
