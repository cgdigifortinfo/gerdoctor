"""Pure rules for Stripe subscription linking and access state."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from slices.stripe_subscription.models import (
    ConnectionReport, PartnerSubscription, SubscriptionLink,
    SubscriptionWebhookAction,
)

USABLE_SUBSCRIPTION_STATUSES = frozenset({"active", "trialing", "past_due", "unpaid", "incomplete"})
UNLOCKED_BILLING_STATUSES = frozenset({"active", "trialing", "paid"})


class SubscriptionRuleError(ValueError): pass
class ForeignCheckoutSession(SubscriptionRuleError): pass
class MissingSubscriptionPrice(SubscriptionRuleError): pass
class MissingStripeCustomer(SubscriptionRuleError): pass


def normalized_emails(values: Iterable[str | None]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value.strip().lower() for value in values if value and value.strip()))


def unique_live_customers(customers: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_id = {str(customer["id"]): dict(customer) for customer in customers if customer.get("id") and not customer.get("deleted")}
    return list(by_id.values())


def subscription_candidates(subscriptions: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(subscription) for subscription in subscriptions]
    usable = [item for item in rows if item.get("status") in USABLE_SUBSCRIPTION_STATUSES]
    return usable or [item for item in rows if item.get("status") != "canceled"]


def billing_status_matches(current: str | None, proposed: str) -> bool:
    return current in ({"paid", "active"} if proposed == "active" else {proposed})


def connection_report(partner: PartnerSubscription, emails: tuple[str, ...], issues: Iterable[str],
                      customer: Mapping[str, Any] | None, subscription: Mapping[str, Any] | None,
                      customer_candidate_count: int, subscription_candidate_count: int) -> ConnectionReport:
    proposed_status = str((subscription or {}).get("status") or partner.billing_status or "pending")
    all_issues = list(issues)
    if subscription and not billing_status_matches(partner.billing_status, proposed_status):
        all_issues.append(f"Lokaler Zahlungsstatus passt nicht zum Stripe-Status „{proposed_status}“.")
    proposed_customer = str((customer or {}).get("id", ""))
    proposed_subscription = str((subscription or {}).get("id", ""))
    needs_repair = bool(all_issues) or (partner.stripe_customer_id or "") != proposed_customer or (partner.stripe_subscription_id or "") != proposed_subscription
    repairable = bool(needs_repair and proposed_customer and proposed_subscription and customer_candidate_count <= 1 and subscription_candidate_count <= 1)
    return ConnectionReport(
        partner.id, partner.name, emails, partner.stripe_customer_id or "",
        partner.stripe_subscription_id or "", partner.billing_status or "",
        tuple(dict.fromkeys(all_issues)), proposed_customer, proposed_subscription,
        proposed_status, repairable,
    )


def checkout_subscription_link(partner_id: str, session: Mapping[str, Any]) -> SubscriptionLink | None:
    if session.get("client_reference_id") != partner_id:
        raise ForeignCheckoutSession
    if session.get("payment_status") != "paid":
        return None
    subscription = session.get("subscription")
    subscription_id = subscription.get("id") if isinstance(subscription, Mapping) else subscription
    return SubscriptionLink(str(session.get("customer") or ""), str(subscription_id or ""), "paid")


def partner_access_unlocked(registration_source: str | None, billing_status: str | None) -> bool:
    return registration_source != "self_service" or billing_status in UNLOCKED_BILLING_STATUSES


def repaired_subscription_link(report: ConnectionReport) -> SubscriptionLink:
    if not report.repairable:
        raise SubscriptionRuleError("connection is not repairable")
    return SubscriptionLink(report.proposed_customer_id, report.proposed_subscription_id, report.proposed_billing_status)


def subscription_webhook_action(event_type: str, event_object: Mapping[str, Any],
                                timestamp: str) -> SubscriptionWebhookAction | None:
    if event_type == "checkout.session.completed" and event_object.get("payment_status") == "paid":
        return SubscriptionWebhookAction({
            "billing_status": "paid", "access_unlocked": True,
            "stripe_customer_id": event_object.get("customer"),
            "stripe_subscription_id": event_object.get("subscription"),
            "paid_at": timestamp,
        }, sync_pending_usage=True)
    if event_type in {"invoice.paid", "customer.subscription.updated"}:
        if event_type == "invoice.paid" or event_object.get("status") in {"active", "trialing"}:
            return SubscriptionWebhookAction({"billing_status": "active", "access_unlocked": True})
        return None
    if event_type == "invoice.payment_failed":
        return SubscriptionWebhookAction({"billing_status": "past_due", "access_unlocked": False})
    if event_type == "customer.subscription.deleted":
        return SubscriptionWebhookAction({"billing_status": "cancelled", "access_unlocked": False})
    return None
