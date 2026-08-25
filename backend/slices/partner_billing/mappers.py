"""Explicit adapters between Mongo-shaped mappings and billing domain values."""
from __future__ import annotations

from typing import Any, Mapping

from slices.partner_billing.models import (
    BillingSettings,
    BillingUser,
    ChargeStatus,
    Money,
    PartnerAccount,
    PriceSource,
    ServiceStep,
    UploadReference,
    UsageCharge,
)


DEFAULT_CURRENCY = "eur"


def document_id(document: Mapping[str, Any]) -> str:
    return str(document.get("id") or document.get("_id") or "")


def partner_from_document(document: Mapping[str, Any]) -> PartnerAccount:
    billing = document.get("billing_settings") or {}
    return PartnerAccount(
        id=document_id(document),
        name=str(document.get("name") or ""),
        stripe_customer_id=document.get("stripe_customer_id"),
        stripe_subscription_id=document.get("stripe_subscription_id"),
        default_currency=str(billing.get("default_currency") or "eur"),
        step_prices=document.get("step_user_fee_cents") or {},
    )


def user_from_document(document: Mapping[str, Any]) -> BillingUser:
    return BillingUser(id=document_id(document), name=str(document.get("name") or ""))


def service_step_from_document(document: Mapping[str, Any] | None) -> ServiceStep | None:
    if document is None:
        return None
    return ServiceStep(
        id=document_id(document),
        title=str(document.get("title") or ""),
        fee_cents=document.get("partner_user_fee_cents"),
    )


def upload_from_document(document: Mapping[str, Any]) -> UploadReference:
    return UploadReference(file_id=document.get("file_id"))


def settings_from_document(document: Mapping[str, Any]) -> BillingSettings:
    return BillingSettings(
        default_fee_cents=int(document.get("stripe_partner_user_fee_cents") or 0),
        currency=document.get("stripe_partner_user_fee_currency"),
    )


def charge_from_document(document: Mapping[str, Any]) -> UsageCharge:
    return UsageCharge(
        id=document_id(document),
        partner_id=str(document["partner_id"]),
        partner_name=str(document.get("partner_name") or ""),
        user_id=str(document["user_id"]),
        user_name=str(document.get("user_name") or ""),
        money=Money(int(document.get("amount") or 0), str(document.get("currency") or DEFAULT_CURRENCY)),
        status=ChargeStatus(str(document.get("status") or ChargeStatus.PENDING.value)),
        service_step_id=str(document.get("service_step_id") or ""),
        service_step_title=str(document.get("service_step_title") or ""),
        price_source=PriceSource(str(document.get("price_source") or PriceSource.GLOBAL.value)),
        first_upload_file_id=document.get("first_upload_file_id"),
        created_at=str(document.get("created_at") or ""),
    )
