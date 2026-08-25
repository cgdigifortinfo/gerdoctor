"""Partner-facing subscription and billing-settings application boundary."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Protocol, cast

from infrastructure.mongo_ids import object_id_or_none
from slices.partner_billing.domain import effective_partner_user_fee
from slices.stripe_subscription.administration import subscription_partner
from slices.stripe_subscription.domain import partner_access_unlocked
from slices.stripe_subscription.models import CheckoutIdentity, CheckoutSettings
from slices.stripe_subscription.service import StripeSubscriptionService


class PartnerPortalNotLinked(ValueError): pass
class PartnerPortalPartnerNotFound(LookupError): pass


class PartnerPortalRepository(Protocol):
    async def partner(self, partner_id: str) -> dict[str, Any] | None: ...
    async def settings(self) -> dict[str, Any]: ...
    async def service_steps(self, partner: Mapping[str, Any]) -> list[dict[str, Any]]: ...
    async def update_billing_settings(self, partner_id: str, fields: Mapping[str, Any]) -> None: ...


class MongoPartnerPortalRepository:
    def __init__(self, database: Any) -> None:
        self._database = database

    async def partner(self, partner_id: str) -> dict[str, Any] | None:
        object_id = object_id_or_none(partner_id)
        if object_id is None:
            return None
        return cast(dict[str, Any] | None, await self._database.partners.find_one({"_id": object_id}))

    async def settings(self) -> dict[str, Any]:
        return cast(dict[str, Any], await self._database.site_settings.find_one({"_key": "global"}) or {})

    async def service_steps(self, partner: Mapping[str, Any]) -> list[dict[str, Any]]:
        query: dict[str, Any] = {
            "step_type": {"$in": ["partner_selection", "partner_multiselection"]},
            "is_active": True,
            "filter_tag": {"$in": list(partner.get("tags") or [])},
        }
        if partner.get("survey_ids"):
            query["survey_id"] = {"$in": list(partner["survey_ids"])}
        return cast(list[dict[str, Any]], await self._database.steps.find(query).sort([
            ("survey_id", 1), ("order", 1),
        ]).to_list(1000))

    async def update_billing_settings(
        self, partner_id: str, fields: Mapping[str, Any],
    ) -> None:
        object_id = object_id_or_none(partner_id)
        if object_id is not None:
            await self._database.partners.update_one({"_id": object_id}, {"$set": {
                f"billing_settings.{key}": value for key, value in fields.items()
            }})


Usage = Callable[[str], Awaitable[dict[str, Any]]]
PublicStripe = Callable[[], Awaitable[dict[str, Any]]]
Invoices = Callable[[str], Awaitable[list[dict[str, Any]]]]


class PartnerPortalService:
    def __init__(
        self, repository: PartnerPortalRepository, subscriptions: StripeSubscriptionService,
        usage: Usage, public_stripe: PublicStripe, invoices: Invoices, frontend_url: str,
    ) -> None:
        self._repository = repository
        self._subscriptions = subscriptions
        self._usage = usage
        self._public_stripe = public_stripe
        self._invoices = invoices
        self._frontend_url = frontend_url.rstrip("/")

    async def own_partner(self, user: Mapping[str, Any]) -> dict[str, Any]:
        partner_id = user.get("partner_id")
        if not partner_id:
            raise PartnerPortalNotLinked
        partner = await self._repository.partner(str(partner_id))
        if partner is None:
            raise PartnerPortalPartnerNotFound(str(partner_id))
        return partner

    async def settings(self, partner: Mapping[str, Any]) -> dict[str, Any]:
        site = await self._repository.settings()
        pricing = []
        for step in await self._repository.service_steps(partner):
            view = {**step, "id": str(step["_id"])}
            amount, source = effective_partner_user_fee(site, view, dict(partner))
            pricing.append({
                "step_id": view["id"], "step_title": step.get("title", ""),
                "step_order": step.get("order", 0), "amount": amount,
                "currency": str(site.get("stripe_partner_user_fee_currency") or "eur").lower(),
                "source": source,
            })
        return {
            "settings": partner.get("billing_settings", {}),
            "stripe": await self._public_stripe(),
            "billing_status": partner.get("billing_status", "paid"),
            "payment_configured": bool(site.get("stripe_partner_price_id")),
            "usage": await self._usage(str(partner["_id"])),
            "pricing": pricing,
        }

    async def status(self, partner: Mapping[str, Any], session_id: str | None, timestamp: str) -> dict[str, Any]:
        billing_status = await self._subscriptions.checkout_status(
            subscription_partner(partner), session_id, timestamp,
        )
        return {"billing_status": billing_status, "access_unlocked": partner_access_unlocked(
            partner.get("registration_source"), billing_status,
        )}

    async def checkout(self, user: Mapping[str, Any], partner: Mapping[str, Any]) -> str:
        settings = await self._repository.settings()
        return await self._subscriptions.checkout(
            subscription_partner(partner), CheckoutIdentity(str(user["email"]), str(user["name"])),
            CheckoutSettings(settings.get("stripe_partner_price_id"),
                             bool(settings.get("stripe_automatic_tax", False)),
                             bool(settings.get("stripe_allow_promotion_codes", False))),
            f"{self._frontend_url}/partner-payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            f"{self._frontend_url}/partner-payment/cancelled",
        )

    async def portal(self, partner: Mapping[str, Any]) -> str:
        return await self._subscriptions.portal(
            subscription_partner(partner), f"{self._frontend_url}/partner-dashboard?tab=billing",
        )

    async def update_settings(self, partner_id: str, values: Mapping[str, Any]) -> list[str]:
        fields = {key: (value.lower() if key in {"country", "default_currency"} and value else value)
                  for key, value in values.items() if value is not None}
        await self._repository.update_billing_settings(partner_id, fields)
        return list(fields)

    async def stripe_status(self, partner: Mapping[str, Any]) -> dict[str, Any]:
        return {**await self._public_stripe(),
                "billing_status": partner.get("billing_status", "paid"),
                "customer_created": bool(partner.get("stripe_customer_id"))}

    async def invoices(self, partner: Mapping[str, Any]) -> list[dict[str, Any]]:
        customer_id = partner.get("stripe_customer_id")
        return await self._invoices(str(customer_id)) if customer_id else []
