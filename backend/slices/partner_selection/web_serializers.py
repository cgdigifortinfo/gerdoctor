"""Public HTTP representations of partner documents."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def public_partner_summary(partner: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(partner.get("_id") or partner.get("id") or ""),
        "name": str(partner.get("name") or ""),
        "description": str(partner.get("description") or ""),
        "logo_url": partner.get("logo_url"),
        "website": partner.get("website"),
        "category": partner.get("category"),
        "tags": partner.get("tags") if isinstance(partner.get("tags"), list) else [],
    }


def public_partner_detail(partner: Mapping[str, Any]) -> dict[str, Any]:
    return {**public_partner_summary(partner), "contact_email": partner.get("contact_email")}
