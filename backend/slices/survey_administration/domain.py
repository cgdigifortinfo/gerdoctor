"""Pure survey lifecycle rules."""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any
from slices.survey_administration.models import SurveyDraft

def normalized_slug(value: object) -> str:
    return str(value).strip().lower().replace(" ", "-") if value is not None else ""

def survey_document(draft: SurveyDraft, timestamp: str) -> dict[str, Any]:
    return {"name": draft.name, "slug": normalized_slug(draft.slug),
            "description": draft.description or "", "audience": draft.audience or "",
            "is_active": draft.is_active, "is_default": draft.is_default,
            "theme": dict(draft.theme or {}), "created_at": timestamp, "updated_at": timestamp}

def survey_update(values: Mapping[str, Any], timestamp: str) -> dict[str, Any]:
    result = {key: value for key, value in values.items() if value is not None}
    if "slug" in result: result["slug"] = normalized_slug(result["slug"])
    if "theme" in result: result["theme"] = dict(result["theme"])
    result["updated_at"] = timestamp
    return result

def survey_view(document: Mapping[str, Any]) -> dict[str, Any]:
    return {"id": str(document["_id"]), "name": document.get("name", ""),
            "slug": document.get("slug", ""), "description": document.get("description", ""),
            "audience": document.get("audience", ""), "is_active": document.get("is_active", True),
            "is_default": document.get("is_default", False), "theme": document.get("theme", {}),
            "created_at": document.get("created_at"), "updated_at": document.get("updated_at")}

def default_survey_document(slug: str, timestamp: str) -> dict[str, Any]:
    return survey_document(SurveyDraft(
        "Ärzte Anerkennung", slug,
        "Anerkennungs- und Arbeitseinstiegsprozess fuer internationale Aerztinnen und Aerzte.",
        "Internationale Aerztinnen und Aerzte", True, True), timestamp)
