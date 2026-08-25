"""Mongo migration adapter for canonical step field configuration."""
from __future__ import annotations

from typing import Any

from slices.step_configuration.domain import FORM_SCHEMA_VERSION, normalize_document


async def migrate_database_step_configurations(database: Any) -> int:
    updated = 0
    async for step in database.steps.find({}):
        normalized = normalize_document(step)
        if step.get("form_schema_version") == FORM_SCHEMA_VERSION and step.get("fields", []) == normalized["fields"]:
            continue
        await database.steps.update_one(
            {"_id": step["_id"]},
            {"$set": {"fields": normalized["fields"], "form_schema_version": FORM_SCHEMA_VERSION}},
        )
        updated += 1
    return updated
