"""Pure rules for storing and instantiating reusable step templates."""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any

NON_REUSABLE_FIELDS = frozenset({"_id", "id", "order", "is_active", "created_at", "updated_at"})


def sanitize_template_config(config: object) -> dict[str, Any]:
    if not isinstance(config, dict):
        return {}
    return {key: value for key, value in config.items() if key not in NON_REUSABLE_FIELDS}


def template_document(name: str, description: str | None, config: object,
                      timestamp: str) -> dict[str, Any]:
    return {"name": name, "description": description or "",
            "config": sanitize_template_config(config), "created_at": timestamp}


def template_update(values: Mapping[str, Any], timestamp: str) -> dict[str, Any]:
    update = {key: value for key, value in values.items() if value is not None}
    if "config" in update:
        update["config"] = sanitize_template_config(update["config"])
    update["updated_at"] = timestamp
    return update


def template_view(document: Mapping[str, Any]) -> dict[str, Any]:
    return {"id": str(document["_id"]), "name": document.get("name", ""),
            "description": document.get("description", ""), "config": document.get("config", {}),
            "created_at": document.get("created_at")}


def step_source_config(step: Mapping[str, Any]) -> dict[str, Any]:
    return sanitize_template_config(dict(step))


def instantiated_step(config: object, survey_id: str, order: int, timestamp: str) -> dict[str, Any]:
    result = sanitize_template_config(config)
    result.update({"survey_id": survey_id, "order": order, "is_active": True,
                   "is_deleted": False, "current_version": 1, "created_at": timestamp})
    return result


def admin_actor(admin: Mapping[str, Any]) -> dict[str, str]:
    return {"id": str(admin["_id"]), "email": str(admin["email"]), "role": "admin"}
