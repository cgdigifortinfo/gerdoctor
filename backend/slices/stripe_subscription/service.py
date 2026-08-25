"""Application service for Stripe subscription lifecycle operations."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from slices.stripe_subscription.domain import (
    MissingStripeCustomer, MissingSubscriptionPrice, checkout_subscription_link,
    connection_report, normalized_emails, repaired_subscription_link,
    subscription_candidates, unique_live_customers,
)
from slices.stripe_subscription.models import (
    CheckoutIdentity, CheckoutSettings, ConnectionReport, PartnerSubscription,
)
from slices.stripe_subscription.ports import (
    StripeSubscriptionGateway, StripeSubscriptionRepository, UsageSynchronizer,
)


class StripeSubscriptionService:
    def __init__(self, repository: StripeSubscriptionRepository,
                 gateway: StripeSubscriptionGateway, sync_usage: UsageSynchronizer) -> None:
        self._repository = repository
        self._gateway = gateway
        self._sync_usage = sync_usage

    async def checkout(self, partner: PartnerSubscription, identity: CheckoutIdentity,
                       settings: CheckoutSettings, success_url: str, cancel_url: str) -> str:
        if not settings.price_id:
            raise MissingSubscriptionPrice
        customer_id = partner.stripe_customer_id
        if not customer_id:
            customer = await self._gateway.create_customer(identity.email, partner.name or identity.name, partner.id)
            customer_id = str(customer["id"])
            await self._repository.save_customer(partner.id, customer_id)
        session = await self._gateway.create_checkout(
            customer_id, settings.price_id, partner.id, success_url, cancel_url,
            settings.automatic_tax, settings.promotion_codes,
        )
        return str(session["url"])

    async def checkout_status(self, partner: PartnerSubscription, session_id: str | None,
                              timestamp: str) -> str:
        status = partner.billing_status or "paid"
        if session_id:
            session = await self._gateway.checkout_session(session_id)
            link = checkout_subscription_link(partner.id, session)
            if link is not None:
                await self._repository.save_link(partner.id, link, timestamp)
                status = link.billing_status
        return status

    async def portal(self, partner: PartnerSubscription, return_url: str) -> str:
        if not partner.stripe_customer_id:
            raise MissingStripeCustomer
        session = await self._gateway.create_portal(partner.stripe_customer_id, return_url)
        return str(session["url"])

    async def connection_report(self, partner: PartnerSubscription) -> ConnectionReport:
        email = await self._repository.user_email(partner)
        emails = normalized_emails((partner.contact_email, email))
        issues: list[str] = []
        customer: dict[str, Any] | None = None
        customers: list[dict[str, Any]] = []
        if partner.stripe_customer_id:
            try:
                candidate = await self._gateway.retrieve_customer(partner.stripe_customer_id)
                if candidate.get("deleted"):
                    issues.append("Der gespeicherte Stripe-Kunde wurde gelöscht.")
                else:
                    customer = candidate
            except Exception:
                issues.append("Die gespeicherte Stripe-Customer-ID ist ungültig oder nicht erreichbar.")
        else:
            issues.append("Stripe-Customer-ID fehlt.")
        if customer is None:
            discovered: list[Mapping[str, Any]] = []
            for address in emails:
                try:
                    discovered.extend(await self._gateway.customers_by_email(address))
                except Exception:
                    continue
            customers = unique_live_customers(discovered)
            if len(customers) == 1:
                customer = customers[0]
            elif len(customers) > 1:
                issues.append(f"Mehrdeutige Zuordnung: {len(customers)} Stripe-Kunden passen zur E-Mail-Adresse.")
            else:
                issues.append("Kein Stripe-Kunde zur Partner-E-Mail gefunden.")

        subscription: dict[str, Any] | None = None
        subscriptions: list[dict[str, Any]] = []
        if partner.stripe_subscription_id:
            try:
                candidate = await self._gateway.retrieve_subscription(partner.stripe_subscription_id)
                if customer and candidate.get("customer") != customer.get("id"):
                    issues.append("Die gespeicherte Subscription gehört zu einem anderen Stripe-Kunden.")
                else:
                    subscription = candidate
            except Exception:
                issues.append("Die gespeicherte Stripe-Subscription-ID ist ungültig oder nicht erreichbar.")
        else:
            issues.append("Stripe-Subscription-ID fehlt.")
        if customer and subscription is None:
            try:
                subscriptions = subscription_candidates(await self._gateway.subscriptions_for_customer(str(customer["id"])))
                if len(subscriptions) == 1:
                    subscription = subscriptions[0]
                elif len(subscriptions) > 1:
                    issues.append(f"Mehrdeutige Zuordnung: {len(subscriptions)} Stripe-Abonnements sind verwendbar.")
                else:
                    issues.append("Kein verwendbares Stripe-Abonnement gefunden.")
            except Exception:
                issues.append("Stripe-Abonnements konnten nicht geprüft werden.")
        return connection_report(partner, emails, issues, customer, subscription, len(customers), len(subscriptions))

    async def repair(self, partner: PartnerSubscription, report: ConnectionReport, timestamp: str) -> bool:
        if not report.repairable:
            return False
        link = repaired_subscription_link(report)
        await self._repository.save_link(partner.id, link, timestamp, repaired=True)
        await self._sync_usage(partner.id)
        return True
