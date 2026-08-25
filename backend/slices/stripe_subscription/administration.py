"""Administrative Stripe connection audit and repair workflows."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol, cast

from infrastructure.mongo_ids import object_id_or_none
from slices.stripe_subscription.models import ConnectionReport, PartnerSubscription
from slices.stripe_subscription.service import StripeSubscriptionService


class StripeConnectionPartnerNotFound(LookupError):
    pass


class StripeConnectionInvalidPartnerId(ValueError):
    pass


def subscription_partner(document: Mapping[str, Any]) -> PartnerSubscription:
    return PartnerSubscription(
        id=str(document["_id"]),
        name=str(document.get("name", "")),
        contact_email=document.get("contact_email"),
        user_id=document.get("user_id"),
        stripe_customer_id=document.get("stripe_customer_id"),
        stripe_subscription_id=document.get("stripe_subscription_id"),
        billing_status=document.get("billing_status"),
        registration_source=document.get("registration_source"),
    )


class StripeConnectionAdministrationRepository(Protocol):
    async def self_service_partners(self) -> list[dict[str, Any]]: ...
    async def partner(self, partner_id: str) -> dict[str, Any] | None: ...


class MongoStripeConnectionAdministrationRepository:
    def __init__(self, database: Any) -> None:
        self._database = database

    async def self_service_partners(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], await self._database.partners.find({
            "registration_source": "self_service",
        }).sort("name", 1).to_list(1000))

    async def partner(self, partner_id: str) -> dict[str, Any] | None:
        object_id = object_id_or_none(partner_id)
        if object_id is None:
            raise StripeConnectionInvalidPartnerId(partner_id)
        return cast(dict[str, Any] | None, await self._database.partners.find_one({"_id": object_id}))


class StripeConnectionAdministrationService:
    def __init__(
        self, repository: StripeConnectionAdministrationRepository,
        subscriptions: StripeSubscriptionService, timestamp: Callable[[], str],
    ) -> None:
        self._repository = repository
        self._subscriptions = subscriptions
        self._timestamp = timestamp

    async def audit(self) -> dict[str, Any]:
        reports = []
        for partner in await self._repository.self_service_partners():
            report = await self._subscriptions.connection_report(subscription_partner(partner))
            if report.issues or report.repairable:
                reports.append(report.to_document())
        return {
            "entries": reports,
            "defective": len(reports),
            "repairable": sum(bool(report["repairable"]) for report in reports),
        }

    async def repair_all(self) -> tuple[list[str], list[str]]:
        repaired: list[str] = []
        skipped: list[str] = []
        for partner in await self._repository.self_service_partners():
            typed_partner = subscription_partner(partner)
            report = await self._subscriptions.connection_report(typed_partner)
            if await self._subscriptions.repair(typed_partner, report, self._timestamp()):
                repaired.append(typed_partner.id)
            elif report.issues:
                skipped.append(typed_partner.id)
        return repaired, skipped

    async def repair(self, partner_id: str) -> ConnectionReport | None:
        partner = await self._repository.partner(partner_id)
        if partner is None:
            raise StripeConnectionPartnerNotFound(partner_id)
        typed_partner = subscription_partner(partner)
        report = await self._subscriptions.connection_report(typed_partner)
        repaired = await self._subscriptions.repair(typed_partner, report, self._timestamp())
        return report if repaired else None
