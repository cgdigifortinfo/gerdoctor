"""Pure planning and presentation rules for partner administration."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from slices.partner_administration.models import PartnerUpdatePlan


PAID_BILLING_STATUSES = frozenset({"active", "trialing", "paid"})


def create_partner_document(data: Mapping[str, Any], created_at: str) -> dict[str, Any]:
    survey_ids = tuple(data.get("survey_ids") or ())
    supplied_surveys = data.get("survey_ids") is not None
    return {
        "name": data["name"],
        "description": data["description"],
        "logo_url": data.get("logo_url"),
        "website": data.get("website"),
        "contact_email": data.get("contact_email"),
        "category": data.get("category"),
        "tags": list(data.get("tags") or ()),
        "linked_user_ids": list(data.get("linked_user_ids") or ()),
        "survey_ids": list(survey_ids),
        "step_user_fee_cents": dict(data.get("step_user_fee_cents") or {}),
        "stripe_customer_id": data.get("stripe_customer_id"),
        "stripe_subscription_id": data.get("stripe_subscription_id"),
        "billing_status": data.get("billing_status") or "pending",
        "is_active": bool(survey_ids) if supplied_surveys else True,
        "registration_status": "active",
        "registration_source": "admin",
        "created_at": created_at,
    }


def partner_update_plan(data: Mapping[str, Any], updated_at: str) -> PartnerUpdatePlan:
    fields = {key: value for key, value in data.items() if value is not None}
    fields["updated_at"] = updated_at
    survey_values = data.get("survey_ids")
    survey_ids = tuple(dict.fromkeys(survey_values)) if survey_values is not None else None
    if survey_ids is not None:
        fields["survey_ids"] = list(survey_ids)
        fields["is_active"] = bool(survey_ids)
        fields["registration_status"] = "active" if survey_ids else "pending"
    prices = data.get("step_user_fee_cents")
    priced_step_ids = tuple(prices) if prices is not None else None
    billing_status = data.get("billing_status")
    if billing_status is not None:
        fields["access_unlocked"] = billing_status in PAID_BILLING_STATUSES
    return PartnerUpdatePlan(fields, survey_ids, priced_step_ids)


def service_steps_for_partner(partner: Mapping[str, Any], steps: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    tags = set(partner.get("tags") or ())
    surveys = set(partner.get("survey_ids") or ())
    return [{
        "id": str(step["_id"]), "title": step.get("title", ""), "order": step.get("order", 0),
        "survey_id": step.get("survey_id"), "filter_tag": step.get("filter_tag", ""),
        "step_user_fee_cents": step.get("partner_user_fee_cents"),
    } for step in steps if step.get("filter_tag") in tags and (
        not surveys or step.get("survey_id") in surveys
    )]


def partner_admin_record(partner: Mapping[str, Any], linked_users: Iterable[Mapping[str, Any]],
                         pending_registrations: int, service_steps: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    active = partner.get("is_active", True)
    return {
        "id": str(partner["_id"]), "name": partner["name"],
        "description": partner.get("description", ""), "logo_url": partner.get("logo_url"),
        "website": partner.get("website"), "contact_email": partner.get("contact_email"),
        "category": partner.get("category"), "tags": partner.get("tags", []), "is_active": active,
        "user_id": partner.get("user_id"), "linked_users": list(linked_users),
        "linked_user_ids": partner.get("linked_user_ids", []),
        "pending_registrations": pending_registrations, "survey_ids": partner.get("survey_ids", []),
        "registration_status": partner.get("registration_status", "active" if active else "pending"),
        "registration_source": partner.get("registration_source", "admin"),
        "registered_at": partner.get("registered_at", partner.get("created_at")),
        "stripe_account_id": partner.get("stripe_account_id"),
        "stripe_onboarding_complete": partner.get("stripe_onboarding_complete", False),
        "stripe_customer_id": partner.get("stripe_customer_id", ""),
        "stripe_subscription_id": partner.get("stripe_subscription_id", ""),
        "billing_status": partner.get("billing_status", ""),
        "step_user_fee_cents": partner.get("step_user_fee_cents", {}),
        "service_steps": list(service_steps),
    }


def sorted_partner_records(records: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(records, key=lambda partner: ((partner.get("name") or "").casefold(), str(partner.get("_id") or "")))


def user_role_update(role: str, group_id: str | None, partner_id: str | None = None) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "role": role, "group_ids": [group_id] if group_id else [],
        "permission_overrides": {"allow": [], "deny": []},
    }
    if partner_id is not None:
        fields["partner_id"] = partner_id
    return fields
