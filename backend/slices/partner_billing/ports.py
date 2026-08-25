"""Typed ports implemented by infrastructure adapters."""
from __future__ import annotations

from typing import Any, Protocol

from slices.partner_billing.models import BillingSettings, UsageCharge


class BillingRepository(Protocol):
    async def global_settings(self) -> BillingSettings: ...
    async def find_charge(self, partner_id: str, user_id: str, service_step_id: str) -> UsageCharge | None: ...
    async def insert_charge(self, charge: UsageCharge) -> None: ...
    async def usage_rows(self, partner_id: str) -> list[UsageCharge]: ...
    async def pending_sync_rows(self, partner_id: str) -> list[UsageCharge]: ...
    async def mark_sync_error(self, charge_id: str, message: str) -> None: ...
    async def mark_queued(self, charge_id: str, item_id: str | None, queued_at: str) -> None: ...


class StripeInvoiceGateway(Protocol):
    async def __call__(
        self,
        customer_id: str,
        subscription_id: str,
        amount: int,
        currency: str,
        description: str,
        metadata: dict[str, str],
    ) -> dict[str, Any]: ...
