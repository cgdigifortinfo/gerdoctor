"""Allow-listed Stripe billing representations for portal responses."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


INVOICE_FIELDS = (
    "id", "number", "status", "amount_due", "amount_paid", "currency",
    "created", "period_start", "period_end", "invoice_pdf",
    "hosted_invoice_url", "livemode",
)


def invoice_view(invoice: Mapping[str, Any]) -> dict[str, Any]:
    return {key: invoice.get(key) for key in INVOICE_FIELDS}
