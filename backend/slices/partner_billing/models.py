"""Immutable domain values for partner usage billing."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class ChargeStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    BILLED = "billed"


class PriceSource(str, Enum):
    GLOBAL = "global"
    STEP = "step"
    PARTNER_STEP = "partner_step"


@dataclass(frozen=True, slots=True)
class Money:
    cents: int
    currency: str = "eur"

    def __post_init__(self) -> None:
        if self.cents < 0:
            raise ValueError("Money cannot be negative")
        normalized = self.currency.strip().lower()
        if len(normalized) != 3:
            raise ValueError("Currency must be a three-letter code")
        object.__setattr__(self, "currency", normalized)


@dataclass(frozen=True, slots=True)
class PartnerAccount:
    id: str
    name: str = ""
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    default_currency: str = "eur"
    step_prices: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_prices", dict(self.step_prices or {}))


@dataclass(frozen=True, slots=True)
class BillingUser:
    id: str
    name: str = ""


@dataclass(frozen=True, slots=True)
class ServiceStep:
    id: str
    title: str = ""
    fee_cents: int | None = None


@dataclass(frozen=True, slots=True)
class UploadReference:
    file_id: str | None = None


@dataclass(frozen=True, slots=True)
class BillingSettings:
    default_fee_cents: int = 0
    currency: str | None = None


@dataclass(frozen=True, slots=True)
class UsageCharge:
    id: str
    partner_id: str
    partner_name: str
    user_id: str
    user_name: str
    money: Money
    status: ChargeStatus
    service_step_id: str
    service_step_title: str
    price_source: PriceSource
    first_upload_file_id: str | None
    created_at: str

    def to_document(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "partner_id": self.partner_id,
            "partner_name": self.partner_name,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "amount": self.money.cents,
            "currency": self.money.currency,
            "status": self.status.value,
            "service_step_id": self.service_step_id,
            "service_step_title": self.service_step_title,
            "price_source": self.price_source.value,
            "first_upload_file_id": self.first_upload_file_id,
            "created_at": self.created_at,
        }


@dataclass(frozen=True, slots=True)
class BillingStats:
    pending_users: int
    pending_amount: int
    billed_users: int
    billed_amount: int
    currency: str
    pending: tuple[UsageCharge, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pending_users": self.pending_users,
            "pending_amount": self.pending_amount,
            "billed_users": self.billed_users,
            "billed_amount": self.billed_amount,
            "currency": self.currency,
            "pending": [charge.to_document() for charge in self.pending],
        }
