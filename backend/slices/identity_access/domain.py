"""Pure identity and account-access rules."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from datetime import datetime


def partner_is_awaiting_assignment(partner: Mapping[str, Any] | None) -> bool:
    return not partner or (
        partner.get("registration_status") != "active"
        or partner.get("is_active") is not True
        or not partner.get("survey_ids")
    )

def normalized_email(email: str) -> str: return email.lower()

def user_registration_document(email: str, password_hash: str, name: str, survey: Mapping[str, Any],
                               group_id: str | None, timestamp: str, default_slug: str) -> dict[str, Any]:
    return {"email": normalized_email(email), "password_hash": password_hash, "name": name,
            "role": "user", "profile": {}, "survey_id": str(survey["_id"]),
            "survey_slug": survey.get("slug", default_slug), "created_at": timestamp,
            "group_ids": [group_id] if group_id else [],
            "permission_overrides": {"allow": [], "deny": []}}

def partner_registration_documents(data: Mapping[str, Any], password_hash: str, group_id: str | None,
                                   timestamp: str) -> tuple[dict[str, Any], dict[str, Any]]:
    email = normalized_email(str(data["email"])); country_value = data.get("country")
    country = str(country_value).upper() if country_value else "DE"
    user = {"email": email, "password_hash": password_hash, "name": data["contact_name"],
            "role": "partner", "profile": {}, "created_at": timestamp,
            "group_ids": [group_id] if group_id else [], "permission_overrides": {"allow": [], "deny": []},
            "registration_source": "partner_self_service"}
    partner = {"name": data["company_name"], "description": data.get("description") or "",
               "website": data.get("website"), "contact_email": email, "country": country,
               "category": "", "tags": [], "linked_user_ids": [], "survey_ids": [],
               "is_active": False, "registration_status": "pending", "registration_source": "self_service",
               "registered_at": timestamp, "created_at": timestamp, "billing_status": "pending",
               "access_unlocked": False,
               "billing_settings": {"legal_name": data["company_name"], "country": country,
                                    "default_currency": "eur"}}
    return user, partner

def login_identifier(ip: str, email: str) -> str: return f"{ip}:{normalized_email(email)}"
def login_is_locked(attempt: Mapping[str, Any] | None, now: datetime) -> bool:
    if not attempt or "count" not in attempt or int(attempt["count"]) < 5: return False
    value = attempt.get("lockout_until")
    return bool(value and datetime.fromisoformat(str(value)) > now)

def initial_progress(user_id: str, survey_id: str, steps: Sequence[Mapping[str, Any]], timestamp: str) -> list[dict[str, Any]]:
    return [{"user_id": user_id, "step_id": str(step["_id"]), "survey_id": survey_id,
             "step_order": step.get("order"), "status": "pending", "data": {},
             "created_at": timestamp, "updated_at": timestamp} for step in steps]
