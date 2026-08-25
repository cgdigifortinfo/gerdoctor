"""Pydantic request boundaries for CMS/public-settings HTTP routes."""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class CMSContentUpdate(BaseModel):
    section: str | None = None
    content: dict[str, Any]
    translations: dict[str, Any] | None = None


class SiteSettingsUpdate(BaseModel):
    site_title: str | None = None
    logo_text: str | None = None
    logo_bold_part: str | None = None
    logo_light_part: str | None = None
    contact_email: str | None = None
    footer_text: str | None = None
    primary_color: str | None = None
    meta_description: str | None = None
    ui_show_journey_indicator: bool | None = None
    ui_show_eta_header: bool | None = None
    ui_show_progress_percentage: bool | None = None
    stripe_sandbox_mode: bool | None = None
    stripe_test_publishable_key: str | None = None
    stripe_test_secret_key: str | None = None
    stripe_test_webhook_secret: str | None = None
    stripe_live_publishable_key: str | None = None
    stripe_live_secret_key: str | None = None
    stripe_live_webhook_secret: str | None = None
    stripe_partner_price_id: str | None = None
    stripe_partner_user_fee_cents: int | None = Field(default=None, ge=0)
    stripe_partner_user_fee_currency: str | None = None
    stripe_partner_payment_mode: str | None = None
    stripe_automatic_tax: bool | None = None
    stripe_allow_promotion_codes: bool | None = None
