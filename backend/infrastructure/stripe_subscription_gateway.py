"""Adapter from the subscription port to the shared Stripe HTTP client."""
from __future__ import annotations

from typing import Any

from stripe_service import (
    checkout_session, create_checkout_session, create_customer,
    create_customer_portal, find_customers_by_email,
    list_customer_subscriptions, retrieve_customer, retrieve_subscription,
)


class StripeApiSubscriptionGateway:
    async def create_customer(self, email: str, name: str, partner_id: str) -> dict[str, Any]:
        return await create_customer(email, name, partner_id)

    async def create_checkout(self, customer_id: str, price_id: str, partner_id: str,
                              success_url: str, cancel_url: str, automatic_tax: bool,
                              promotion_codes: bool) -> dict[str, Any]:
        return await create_checkout_session(
            customer_id, price_id, partner_id, success_url, cancel_url,
            "subscription", automatic_tax, promotion_codes,
        )

    async def checkout_session(self, session_id: str) -> dict[str, Any]:
        return await checkout_session(session_id)

    async def create_portal(self, customer_id: str, return_url: str) -> dict[str, Any]:
        return await create_customer_portal(customer_id, return_url)

    async def retrieve_customer(self, customer_id: str) -> dict[str, Any]:
        return await retrieve_customer(customer_id)

    async def customers_by_email(self, email: str) -> list[dict[str, Any]]:
        return list((await find_customers_by_email(email)).get("data", []))

    async def retrieve_subscription(self, subscription_id: str) -> dict[str, Any]:
        return await retrieve_subscription(subscription_id)

    async def subscriptions_for_customer(self, customer_id: str) -> list[dict[str, Any]]:
        return list((await list_customer_subscriptions(customer_id)).get("data", []))
