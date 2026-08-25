"""HTTP error mapping for Stripe subscription operations."""
from fastapi import HTTPException
from pydantic import BaseModel, Field

from slices.stripe_subscription.domain import (
    ForeignCheckoutSession, MissingStripeCustomer, MissingSubscriptionPrice,
)


class PartnerBillingSettingsUpdate(BaseModel):
    legal_name: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country: str | None = None
    tax_id: str | None = None
    default_currency: str | None = Field(default=None, min_length=3, max_length=3)
    invoice_footer: str | None = None
    payment_terms_days: int | None = Field(default=None, ge=0, le=365)


def stripe_subscription_http_error(error: Exception) -> HTTPException:
    if isinstance(error, MissingSubscriptionPrice):
        return HTTPException(status_code=503, detail="Der Partnerpreis wurde im Adminbereich noch nicht konfiguriert")
    if isinstance(error, MissingStripeCustomer):
        return HTTPException(status_code=400, detail="Noch kein Stripe-Kundenkonto vorhanden")
    if isinstance(error, ForeignCheckoutSession):
        return HTTPException(status_code=403, detail="Checkout session does not belong to this partner")
    return HTTPException(status_code=400, detail="Ungültiger Stripe-Abonnementvorgang")
