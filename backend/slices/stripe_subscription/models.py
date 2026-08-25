"""Immutable Stripe subscription values."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PartnerSubscription:
    id: str
    name: str
    contact_email: str | None
    user_id: str | None
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    billing_status: str | None
    registration_source: str | None = None


@dataclass(frozen=True, slots=True)
class CheckoutIdentity:
    email: str
    name: str


@dataclass(frozen=True, slots=True)
class CheckoutSettings:
    price_id: str | None
    automatic_tax: bool = False
    promotion_codes: bool = False


@dataclass(frozen=True, slots=True)
class SubscriptionLink:
    customer_id: str
    subscription_id: str
    billing_status: str


@dataclass(frozen=True, slots=True)
class SubscriptionWebhookAction:
    fields: dict[str, object]
    sync_pending_usage: bool = False


@dataclass(frozen=True, slots=True)
class ConnectionReport:
    partner_id: str
    partner_name: str
    emails: tuple[str, ...]
    current_customer_id: str
    current_subscription_id: str
    current_billing_status: str
    issues: tuple[str, ...]
    proposed_customer_id: str
    proposed_subscription_id: str
    proposed_billing_status: str
    repairable: bool

    def to_document(self) -> dict[str, object]:
        return {
            "partner_id": self.partner_id, "partner_name": self.partner_name,
            "emails": list(self.emails), "current_customer_id": self.current_customer_id,
            "current_subscription_id": self.current_subscription_id,
            "current_billing_status": self.current_billing_status,
            "issues": list(self.issues), "proposed_customer_id": self.proposed_customer_id,
            "proposed_subscription_id": self.proposed_subscription_id,
            "proposed_billing_status": self.proposed_billing_status,
            "repairable": self.repairable,
        }
