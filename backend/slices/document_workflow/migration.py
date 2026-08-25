"""Idempotent migration for legacy document-workflow titles and locks."""
from __future__ import annotations

from typing import Any


async def migrate_document_workflows(database: Any, step_query: Any) -> int:
    settings = await database.site_settings.find_one(
        {"_key": "global"}, {"document_workflow_version": 1},
    ) or {}
    current = int(settings.get("document_workflow_version", 0))
    if current >= 2:
        return 0
    changed = 0
    for survey_id in await database.steps.distinct("survey_id"):
        steps = await database.steps.find(step_query(survey_id)).sort("order", 1).to_list(100)
        decision: dict[str, Any] | None = None
        branches: list[dict[str, Any]] = []
        for step in steps:
            if step.get("step_type") == "decision":
                decision, branches = step, []
                continue
            if decision is None:
                continue
            if step.get("step_type") != "milestone":
                branches.append(step)
                continue
            upload = next((branch for branch in branches if any(
                field.get("field_type") in {"file", "upload", "multiupload"}
                for field in branch.get("fields", [])
            )), None)
            partner = next((branch for branch in branches if branch.get("step_type")
                            in {"partner_selection", "partner_multiselection"}), None)
            if (current < 1 and upload and partner
                    and str(upload.get("title", "")).startswith("Dokumente ")
                    and str(step.get("title", "")).startswith("Übersicht ")):
                await database.steps.update_one({"_id": upload["_id"]}, {"$set": {"title": step["title"]}})
                await database.steps.update_one({"_id": step["_id"]}, {"$set": {"title": upload["title"]}})
                changed += 2
            if upload and partner:
                field = next((item for item in upload.get("fields", []) if item.get("field_type")
                              in {"file", "upload", "multiupload"}), None)
                assert field is not None
                locks = [
                    {"action": "read_only", "source_step_order": upload["order"], "field": field["name"],
                     "operator": "has_upload", "value": "", "message": "Nach dem Dokumenten-Upload ist dieser Schritt schreibgeschützt."},
                    {"action": "read_only", "source_step_order": step["order"], "field": "partner_uploads",
                     "operator": "has_upload", "value": "", "message": "Nach dem Dokumenten-Upload ist dieser Schritt schreibgeschützt."},
                ]
                for target in (decision, upload, partner):
                    conditions = target.get("conditions") or []
                    keys = {(item.get("action"), item.get("source_step_order"), item.get("field"), item.get("operator")) for item in conditions}
                    additions = [lock for lock in locks if (lock["action"], lock["source_step_order"], lock["field"], lock["operator"]) not in keys]
                    if additions:
                        await database.steps.update_one({"_id": target["_id"]}, {"$set": {"conditions": [*conditions, *additions]}})
                        changed += len(additions)
            decision, branches = None, []
    await database.site_settings.update_one(
        {"_key": "global"}, {"$set": {"document_workflow_version": 2}}, upsert=True,
    )
    return changed
