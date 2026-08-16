"""Canonical survey form-builder schema and idempotent migrations."""
from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


FORM_SCHEMA_VERSION = 1

CONTENT_FIELD_TYPES = {"heading", "paragraph", "html", "image", "divider"}
CHOICE_FIELD_TYPES = {"select", "selectbox", "radio", "multiselect", "decision"}
UPLOAD_FIELD_TYPES = {"file", "upload", "multiupload"}
SUPPORTED_FIELD_TYPES = {
    "text", "email", "phone", "number", "textarea", "date", "time",
    "checkbox", *CHOICE_FIELD_TYPES, *UPLOAD_FIELD_TYPES, *CONTENT_FIELD_TYPES,
}


def _slug(value: str, fallback: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]+", "_", (value or "").strip().lower())
    return normalized.strip("_") or fallback


def normalize_step_field(field: dict[str, Any], index: int = 0) -> dict[str, Any]:
    """Upgrade a legacy field without discarding its custom option metadata."""
    result = deepcopy(field or {})
    field_type = str(result.get("field_type") or "text").strip().lower()
    if field_type not in SUPPORTED_FIELD_TYPES:
        field_type = "text"
    result["field_type"] = field_type

    fallback_name = f"{field_type}_{index + 1}"
    result["name"] = _slug(str(result.get("name") or result.get("label") or ""), fallback_name)
    result["id"] = str(result.get("id") or result["name"])
    result["label"] = str(result.get("label") or result.get("content") or result["name"])
    result["required"] = bool(result.get("required", False)) if field_type not in CONTENT_FIELD_TYPES else False
    result["width"] = result.get("width") if result.get("width") in {"full", "half", "third"} else "full"
    result["help_text"] = str(result.get("help_text") or "")

    if field_type in CHOICE_FIELD_TYPES or field_type == "multiupload":
        result["options"] = list(result.get("options") or [])
    if field_type == "textarea":
        result["rows"] = max(2, min(int(result.get("rows") or 4), 20))
    if field_type in UPLOAD_FIELD_TYPES:
        result["accept"] = str(result.get("accept") or ".pdf,.png,.jpg,.jpeg,.doc,.docx")
        result["multiple"] = bool(result.get("multiple", field_type == "multiupload"))
    if field_type == "heading":
        result["heading_level"] = max(2, min(int(result.get("heading_level") or 2), 4))
    if field_type in {"heading", "paragraph", "html"}:
        result["content"] = str(result.get("content") or result.get("label") or "")
    if field_type == "image":
        result["image_url"] = str(result.get("image_url") or "")
        result["alt_text"] = str(result.get("alt_text") or result.get("label") or "")
        result["caption"] = str(result.get("caption") or "")
    return result


def normalize_step_document(step: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(step)
    result["fields"] = [
        normalize_step_field(field, index)
        for index, field in enumerate(result.get("fields") or [])
    ]
    result["form_schema_version"] = FORM_SCHEMA_VERSION
    return result


def migrate_snapshot_form_configs(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Upgrade the embedded baseline during verify and restore operations."""
    migrated = deepcopy(snapshot)
    collections = migrated.get("collections") or {}
    collections["steps"] = [
        normalize_step_document(step)
        for step in collections.get("steps") or []
    ]
    return migrated


async def migrate_database_form_configs(db) -> int:
    """Upgrade all stored steps in place. Safe to run on every startup."""
    updated = 0
    async for step in db.steps.find({}):
        normalized = normalize_step_document(step)
        if (
            step.get("form_schema_version") == FORM_SCHEMA_VERSION
            and step.get("fields", []) == normalized["fields"]
        ):
            continue
        await db.steps.update_one(
            {"_id": step["_id"]},
            {"$set": {
                "fields": normalized["fields"],
                "form_schema_version": FORM_SCHEMA_VERSION,
            }},
        )
        updated += 1
    return updated
