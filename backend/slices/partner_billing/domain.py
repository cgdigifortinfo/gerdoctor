"""Pure business rules for partner usage billing."""
from __future__ import annotations

from typing import Any, Iterable

from slices.partner_billing.mappers import (
    partner_from_document,
    service_step_from_document,
    settings_from_document,
    upload_from_document,
    user_from_document,
)
from slices.partner_billing.models import (
    BillingSettings,
    BillingStats,
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


def resolve_price(
    settings: BillingSettings,
    service_step: ServiceStep | None,
    partner: PartnerAccount,
) -> tuple[int, PriceSource]:
    """Resolve the immutable price using global < step < partner/step precedence."""
    amount = settings.default_fee_cents
    source = PriceSource.GLOBAL
    if service_step and service_step.fee_cents is not None:
        amount = int(service_step.fee_cents)
        source = PriceSource.STEP
    if service_step and service_step.id in partner.step_prices:
        amount = int(partner.step_prices[service_step.id])
        source = PriceSource.PARTNER_STEP
    return amount, source


def create_usage_charge(
    partner: PartnerAccount,
    user: BillingUser,
    upload: UploadReference,
    service_step: ServiceStep | None,
    settings: BillingSettings,
    *,
    charge_id: str,
    created_at: str,
) -> UsageCharge:
    amount, source = resolve_price(settings, service_step, partner)
    currency = settings.currency or partner.default_currency or DEFAULT_CURRENCY
    return UsageCharge(
        id=charge_id,
        partner_id=partner.id,
        partner_name=partner.name,
        user_id=user.id,
        user_name=user.name,
        money=Money(amount, currency),
        status=ChargeStatus.PENDING,
        service_step_id=service_step.id if service_step else "",
        service_step_title=service_step.title if service_step else "",
        price_source=source,
        first_upload_file_id=upload.file_id,
        created_at=created_at,
    )


def billing_stats(rows: Iterable[UsageCharge]) -> BillingStats:
    rows = list(rows)
    pending = tuple(row for row in rows if row.status is not ChargeStatus.BILLED)
    billed = tuple(row for row in rows if row.status is ChargeStatus.BILLED)
    return BillingStats(
        pending_users=len(pending),
        pending_amount=sum(row.money.cents for row in pending),
        billed_users=len(billed),
        billed_amount=sum(row.money.cents for row in billed),
        currency=rows[-1].money.currency if rows else DEFAULT_CURRENCY,
        pending=pending,
    )


def usage_billing_stats(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate immutable ledger rows for the partner billing dashboards."""
    rows = list(rows)
    pending = [row for row in rows if row.get("status") != "billed"]
    billed = [row for row in rows if row.get("status") == "billed"]
    return {
        "pending_users": len(pending),
        "pending_amount": sum(int(row.get("amount", 0)) for row in pending),
        "billed_users": len(billed),
        "billed_amount": sum(int(row.get("amount", 0)) for row in billed),
        "currency": next(
            (row["currency"] for row in reversed(rows) if row.get("currency")),
            "eur",
        ),
        "pending": pending,
    }


def effective_partner_user_fee(
    settings: dict[str, Any],
    service_step: dict[str, Any] | None,
    partner: dict[str, Any],
) -> tuple[int, str]:
    """Resolve price precedence: global < service Step < partner/Step."""
    amount, source = resolve_price(
        settings_from_document(settings),
        service_step_from_document(service_step),
        partner_from_document(partner),
    )
    return amount, source.value


def service_step_for_partner_action(
    steps: list[dict[str, Any]],
    progress: list[dict[str, Any]],
    action_step: dict[str, Any],
    partner: dict[str, Any],
) -> dict[str, Any] | None:
    """Find the nearest preceding service selection for this partner."""
    progress_by_step = {row.get("step_id"): row for row in progress}
    partner_id = str(partner["_id"])
    partner_name = partner.get("name", "")  # pragma: no mutate - None/omitted defaults are equivalent under bool()
    candidates = []
    for step in steps:
        if step.get("step_type") not in {"partner_selection", "partner_multiselection"}:
            continue
        if step.get("order", 0) > action_step.get("order", 0):
            continue
        data = (progress_by_step.get(step["id"]) or {}).get("data") or {}
        selected = {str(value) for value in data.get("selected_partner_ids") or []}
        if data.get("selected_partner_id"):
            selected.add(str(data["selected_partner_id"]))
        selected_by_id = partner_id in selected
        selected_by_legacy_name = bool(
            partner_name and data.get("selected_partner_name") == partner_name
        )
        if selected_by_id or selected_by_legacy_name:
            candidates.append(step)
    return max(candidates, key=lambda item: item.get("order", 0), default=None)


def build_usage_charge(
    partner: dict[str, Any],
    user: dict[str, Any],
    upload: dict[str, Any],
    service_step: dict[str, Any] | None,
    settings: dict[str, Any],
    *,
    charge_id: str,
    created_at: str,
) -> dict[str, Any]:
    """Build the canonical usage-ledger document for one service assignment."""
    return create_usage_charge(
        partner_from_document(partner),
        user_from_document(user),
        upload_from_document(upload),
        service_step_from_document(service_step),
        settings_from_document(settings),
        charge_id=charge_id,
        created_at=created_at,
    ).to_document()


def pending_sync_error(amount: int, customer_id: str | None, subscription_id: str | None) -> str | None:
    """Explain why a pending charge cannot yet be sent to Stripe."""
    if amount <= 0:
        return "Nutzergebühr nicht konfiguriert"
    if not customer_id or not subscription_id:
        return "Stripe-Kunde oder Abonnement fehlt"
    return None


def invoice_item_description(user_name: str, user_id: str) -> str:
    return f"Nutzergebühr – {user_name or user_id}"


def invoice_item_metadata(charge: dict[str, Any]) -> dict[str, str]:
    return {
        "partner_id": charge["partner_id"],
        "user_id": charge["user_id"],
        "service_step_id": charge.get("service_step_id", ""),
        "usage_charge_id": charge["id"],
    }
