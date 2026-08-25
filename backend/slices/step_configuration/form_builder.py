"""Compatibility facade for the extracted Step Configuration slice."""
from __future__ import annotations

from typing import Any

from slices.step_configuration.domain import (
    CHOICE_FIELD_TYPES, CONTENT_FIELD_TYPES, FORM_SCHEMA_VERSION,
    SUPPORTED_FIELD_TYPES, UPLOAD_FIELD_TYPES, normalize_document, normalize_field,
)
from slices.step_configuration.migration import migrate_database_step_configurations


def normalize_step_field(field: dict[str, Any], index: int = 0) -> dict[str, Any]:
    return normalize_field(field, index)


def normalize_step_document(step: dict[str, Any]) -> dict[str, Any]:
    return normalize_document(step)


def migrate_snapshot_form_configs(snapshot: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(snapshot)
    collections = dict(migrated.get("collections") or {})
    migrated["collections"] = collections
    collections["steps"] = [normalize_document(step) for step in collections.get("steps") or []]
    return migrated


async def migrate_database_form_configs(db: Any) -> int:
    return await migrate_database_step_configurations(db)
