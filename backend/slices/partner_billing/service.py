"""Partner usage-billing application service."""
from __future__ import annotations

from typing import Any, Callable

from slices.partner_billing.domain import (
    billing_stats,
    create_usage_charge,
    invoice_item_description,
    invoice_item_metadata,
    pending_sync_error,
)
from slices.partner_billing.models import (
    BillingUser,
    PartnerAccount,
    ServiceStep,
    UploadReference,
    UsageCharge,
)
from slices.partner_billing.repository import DuplicateUsageCharge
from slices.partner_billing.ports import BillingRepository, StripeInvoiceGateway


class PartnerBillingService:
    def __init__(
        self,
        repository: BillingRepository,
        create_invoice_item: StripeInvoiceGateway,
        *,
        id_factory: Callable[[], str],
        clock: Callable[[], str],
    ):
        self._repository = repository
        self._create_invoice_item = create_invoice_item
        self._id_factory = id_factory
        self._clock = clock

    async def stats(self, partner_id: str) -> dict[str, Any]:
        return billing_stats(await self._repository.usage_rows(partner_id)).to_dict()

    async def record_upload(
        self,
        partner: PartnerAccount,
        user: BillingUser,
        upload: UploadReference,
        service_step: ServiceStep | None = None,
    ) -> UsageCharge:
        service_step_id = service_step.id if service_step else ""
        existing = await self._repository.find_charge(partner.id, user.id, service_step_id)
        if existing:
            return existing
        charge = create_usage_charge(
            partner, user, upload, service_step,
            await self._repository.global_settings(),
            charge_id=self._id_factory(), created_at=self._clock(),
        )
        try:
            await self._repository.insert_charge(charge)
        except DuplicateUsageCharge:
            return await self._repository.find_charge(
                partner.id, user.id, service_step_id,
            ) or charge
        reason = pending_sync_error(
            charge.money.cents, partner.stripe_customer_id,
            partner.stripe_subscription_id,
        )
        if reason:
            await self._repository.mark_sync_error(charge.id, reason)
            return charge
        await self._queue_charge(partner, charge)
        return charge

    async def sync_pending(self, partner: PartnerAccount) -> int:
        customer_id = partner.stripe_customer_id
        subscription_id = partner.stripe_subscription_id
        if not customer_id or not subscription_id:
            return 0
        rows = await self._repository.pending_sync_rows(partner.id)
        synced = 0
        for charge in rows:
            if await self._queue_charge(partner, charge):
                synced += 1
        return synced

    async def _queue_charge(self, partner: PartnerAccount, charge: UsageCharge) -> bool:
        customer_id = partner.stripe_customer_id
        subscription_id = partner.stripe_subscription_id
        assert customer_id is not None and subscription_id is not None
        try:
            item = await self._create_invoice_item(
                customer_id, subscription_id,
                charge.money.cents, charge.money.currency,
                invoice_item_description(charge.user_name, charge.user_id),
                invoice_item_metadata(charge.to_document()),
            )
        except Exception as exc:  # external Stripe errors remain ledger-visible
            message = str(getattr(exc, "detail", exc))
            await self._repository.mark_sync_error(charge.id, message)
            return False
        await self._repository.mark_queued(charge.id, item.get("id"), self._clock())
        return True
