"""Pure administrative user lifecycle rules."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

VALID_ROLES = frozenset({"user", "partner", "admin"})


class AdminUserRuleError(ValueError): pass
class InvalidRole(AdminUserRuleError): pass
class InvalidPartnerAssignment(AdminUserRuleError): pass
class PrimaryAdminProtected(AdminUserRuleError): pass
class ConflictingPermissionOverrides(AdminUserRuleError): pass


def validated_role(role: str) -> str:
    if role not in VALID_ROLES: raise InvalidRole
    return role


def validate_partner_assignment(role: str, partner_id: str | None) -> None:
    if partner_id and role != "partner": raise InvalidPartnerAssignment


def search_query(text: str, role: str) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if text:
        query["$or"] = [{"name": {"$regex": text, "$options": "i"}},
                        {"email": {"$regex": text, "$options": "i"}}]
    if role and role != "all": query["role"] = role
    return query


def permission_overrides(allow: Sequence[str], deny: Sequence[str]) -> dict[str, list[str]]:
    if set(allow) & set(deny): raise ConflictingPermissionOverrides
    return {"allow": list(allow), "deny": list(deny)}


def role_fields(role: str, default_group_id: str | None) -> dict[str, Any]:
    validated_role(role)
    return {"role": role, "group_ids": [default_group_id] if default_group_id else [],
            "permission_overrides": {"allow": [], "deny": []}}


def ensure_primary_admin_change(email: str, primary_email: str, new_role: str | None = None) -> None:
    if email == primary_email and new_role != "admin": raise PrimaryAdminProtected


def new_user_document(email: str, password_hash: str, name: str, role: str,
                      group_ids: Sequence[str], timestamp: str,
                      survey: Mapping[str, Any] | None = None,
                      partner_id: str | None = None, default_survey_slug: str = "aerzte") -> dict[str, Any]:
    validated_role(role); validate_partner_assignment(role, partner_id)
    document: dict[str, Any] = {"email": email.strip().lower(), "password_hash": password_hash,
        "name": name, "role": role, "profile": {}, "created_at": timestamp,
        "permission_overrides": {"allow": [], "deny": []}, "group_ids": list(group_ids)}
    if survey:
        document["survey_id"] = str(survey["_id"])
        document["survey_slug"] = survey.get("slug", default_survey_slug)
    if partner_id: document["partner_id"] = partner_id
    return document


def initial_progress(user_id: str, survey_id: str, steps: Sequence[Mapping[str, Any]],
                     timestamp: str) -> list[dict[str, Any]]:
    return [{"user_id": user_id, "step_id": str(step["_id"]), "survey_id": survey_id,
             "step_order": step.get("order"), "status": "pending", "data": {},
             "created_at": timestamp, "updated_at": timestamp} for step in steps]


def archived_user_fields(user_id: str, email: str, original_email: str | None,
                         admin_id: str, timestamp: str) -> dict[str, Any]:
    return {"email": f"deleted+{user_id}+{email}",
            "archived_original_email": original_email or email, "is_deleted": True,
            "deleted_at": timestamp, "deleted_by": admin_id, "is_active": False}
