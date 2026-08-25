"""HTTP mapping for partner administration failures."""
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, field_validator

from slices.partner_administration.service import InvalidPricedStep, UnknownPartner, UnknownSurvey, UnknownUser


class PartnerCreate(BaseModel):
    name: str
    description: str
    logo_url: str | None = None
    website: str | None = None
    contact_email: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    linked_user_ids: list[str] | None = None
    survey_ids: list[str] | None = None
    step_user_fee_cents: dict[str, int] | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    billing_status: str | None = None

    @field_validator("contact_email", mode="before")
    @classmethod
    def empty_str_to_none(cls, value: Any) -> Any:
        return None if value == "" else value

    @field_validator("step_user_fee_cents")
    @classmethod
    def non_negative_step_prices(
        cls, value: dict[str, int] | None,
    ) -> dict[str, int] | None:
        if value and any(amount < 0 for amount in value.values()):
            raise ValueError("step prices cannot be negative")
        return value


class PartnerUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    logo_url: str | None = None
    website: str | None = None
    contact_email: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    is_active: bool | None = None
    linked_user_ids: list[str] | None = None
    survey_ids: list[str] | None = None
    step_user_fee_cents: dict[str, int] | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    billing_status: str | None = None

    @field_validator("contact_email", mode="before")
    @classmethod
    def empty_str_to_none(cls, value: Any) -> Any:
        return None if value == "" else value

    @field_validator("step_user_fee_cents")
    @classmethod
    def non_negative_step_prices(
        cls, value: dict[str, int] | None,
    ) -> dict[str, int] | None:
        if value and any(amount < 0 for amount in value.values()):
            raise ValueError("step prices cannot be negative")
        return value


def partner_administration_http_error(error: Exception) -> HTTPException:
    if isinstance(error, UnknownPartner): return HTTPException(status_code=404, detail="Partner not found")
    if isinstance(error, UnknownUser): return HTTPException(status_code=404, detail="User not found")
    if isinstance(error, UnknownSurvey): return HTTPException(status_code=400, detail="Unknown survey id")
    if isinstance(error, InvalidPricedStep):
        return HTTPException(status_code=400, detail="Partner prices may only reference partner selection steps")
    return HTTPException(status_code=400, detail="Invalid partner administration request")
