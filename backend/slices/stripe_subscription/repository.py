"""MongoDB adapter for Stripe subscription links."""
from __future__ import annotations

from typing import Any

from infrastructure.mongo_ids import object_id_or_none
from slices.stripe_subscription.models import PartnerSubscription, SubscriptionLink


class MongoStripeSubscriptionRepository:
    def __init__(self, database: Any) -> None:
        self._db = database

    async def user_email(self, partner: PartnerSubscription) -> str | None:
        partner_id = partner.id
        user_object_id = object_id_or_none(partner.user_id) if partner.user_id else None
        query: dict[str, Any] = {"$or": [{"partner_id": partner_id}, {"_id": user_object_id}]} if user_object_id is not None else {"partner_id": partner_id}
        user = await self._db.users.find_one(query)
        return str(user.get("email")) if user and user.get("email") else None

    async def save_customer(self, partner_id: str, customer_id: str) -> None:
        object_id = object_id_or_none(partner_id)
        if object_id is not None:
            await self._db.partners.update_one({"_id": object_id}, {"$set": {"stripe_customer_id": customer_id}})

    async def save_link(self, partner_id: str, link: SubscriptionLink, timestamp: str, repaired: bool = False) -> None:
        object_id = object_id_or_none(partner_id)
        if object_id is None:
            return
        fields: dict[str, Any] = {
            "stripe_customer_id": link.customer_id, "stripe_subscription_id": link.subscription_id,
            "billing_status": link.billing_status,
            "access_unlocked": link.billing_status in {"active", "trialing", "paid"},
        }
        fields["stripe_connection_repaired_at" if repaired else "paid_at"] = timestamp
        await self._db.partners.update_one({"_id": object_id}, {"$set": fields})
