#!/usr/bin/env python3
"""Idempotently update the Pflege survey stage chain.

Resulting core stages:
  Anerkennung -> Sprachschule -> Fachsprachenprüfung
  -> Vorbereitungskurs Kenntnisprüfung -> Kenntnisprüfung -> Jobangebote
"""
import asyncio
import os
from copy import deepcopy
from datetime import datetime, timezone

from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient


load_dotenv("/app/backend/.env")


def replace_terms(value):
    replacements = (
        ("Approbation", "Anerkennung"),
        ("Sprachprüfung", "Fachsprachenprüfung"),
    )
    if isinstance(value, str):
        for old, new in replacements:
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [replace_terms(item) for item in value]
    if isinstance(value, dict):
        return {key: replace_terms(item) for key, item in value.items()}
    return value


def wait_for(previous_order):
    return [
        {
            "action": "block", "source_step_order": previous_order, "field": "",
            "operator": "status_not", "value": "completed",
            "message": "Bitte schließen Sie zuerst den vorherigen Meilenstein ab.",
        },
        {
            "action": "hide", "source_step_order": previous_order, "field": "",
            "operator": "status_not", "value": "completed",
        },
    ]


def stage_documents(survey_id, name, decision_order, previous_milestone, tag, now):
    upload_order = decision_order + 1
    partner_order = decision_order + 2
    milestone_order = decision_order + 3
    document_options = [
        "Identitätsnachweis", "Lebenslauf", "Ausbildungsnachweis Pflege",
        "Arbeitszeugnisse", "Sprachnachweis", "Defizitbescheid",
        "Berufsurkunde", "Kursnachweis", "Prüfungsanmeldung", "Sonstiges",
    ]
    common = {
        "survey_id": survey_id,
        "duration_unit": "days",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    return [
        {
            **common,
            "title": name,
            "description": f"Haben Sie {name} bereits geplant oder benötigen Sie Unterstützung?",
            "order": decision_order,
            "step_type": "decision",
            "fields": [{
                "name": "decision", "field_type": "decision", "label": name,
                "required": True,
                "options": [
                    {"value": "upload", "label": "Ich habe Dokumente und möchte sie hochladen"},
                    {"value": "partner", "label": "Ich möchte einen passenden Partner auswählen"},
                ],
            }],
            "required_fields": ["decision"],
            "conditions": wait_for(previous_milestone),
            "duration_value": 0,
        },
        {
            **common,
            "title": f"Dokumente {name}",
            "description": f"Laden Sie Ihre Dokumente für {name} hoch.",
            "order": upload_order,
            "step_type": "form",
            "fields": [{
                "name": "documents", "field_type": "multiupload",
                "label": "Dokumente", "options": document_options, "required": True,
            }],
            "conditions": [{
                "action": "hide", "source_step_order": decision_order,
                "field": "decision", "operator": "not_equals", "value": "upload",
            }],
            "duration_value": 0,
        },
        {
            **common,
            "title": f"Service {name}",
            "description": f"Wählen Sie einen Partner für {name}.",
            "order": partner_order,
            "step_type": "partner_selection",
            "filter_tag": tag,
            "fields": [],
            "conditions": [{
                "action": "hide", "source_step_order": decision_order,
                "field": "decision", "operator": "not_equals", "value": "partner",
            }],
            "duration_value": 0,
        },
        {
            **common,
            "title": f"Übersicht {name}",
            "description": f"Übersicht und Status für {name}.",
            "order": milestone_order,
            "step_type": "milestone",
            "fields": [],
            "conditions": [
                {
                    "action": "auto_complete", "source_step_order": upload_order,
                    "field": "documents", "operator": "has_upload", "value": "",
                },
                {
                    "action": "block",
                    "all_of": [
                        {
                            "source_step_order": decision_order, "field": "decision",
                            "operator": "equals", "value": "upload",
                        },
                        {
                            "source_step_order": upload_order, "field": "documents",
                            "operator": "missing_upload", "value": "",
                        },
                    ],
                    "message": "Bitte laden Sie zuerst die Dokumente im vorigen Schritt hoch.",
                },
                {
                    "action": "hide", "source_step_order": decision_order,
                    "field": "decision", "operator": "empty", "value": "",
                },
            ],
            "duration_value": 6,
            "duration_unit": "weeks",
            "email_on_leave": True,
            "pending_message": "Dieser Schritt wird von Ihrem Partner bearbeitet.",
            "complete_message": "Abgeschlossen!",
        },
    ]


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]
    survey = await db.surveys.find_one({"slug": "pflege"})
    if not survey:
        raise RuntimeError("Survey 'pflege' not found")
    survey_id = str(survey["_id"])
    now = datetime.now(timezone.utc).isoformat()

    steps = await db.steps.find({"survey_id": survey_id}).to_list(200)
    equality_steps = [
        step for step in steps
        if "Gleichwertigkeitsprüfung" in str(step)
        or "Gleichwertigkeitspruefung" in str(step)
    ]
    equality_ids = [str(step["_id"]) for step in equality_steps]
    if equality_steps:
        await db.steps.delete_many({"_id": {"$in": [step["_id"] for step in equality_steps]}})
        await db.user_progress.delete_many({"step_id": {"$in": equality_ids}})

    # Rename every string in Pflege step documents, including tags, labels,
    # messages, translations and nested option text.
    for step in await db.steps.find({"survey_id": survey_id}).to_list(200):
        normalized = replace_terms(deepcopy(step))
        normalized.pop("_id", None)
        normalized["updated_at"] = now
        await db.steps.replace_one({"_id": step["_id"]}, normalized)

    # Make room for the two new four-step stages and reconnect Jobangebote.
    job_steps = await db.steps.find({
        "survey_id": survey_id,
        "title": {"$regex": "Jobangebote"},
    }).sort("order", 1).to_list(10)
    job_orders = {
        "decision": 23,
        "partner_multiselection": 24,
        "milestone": 25,
    }
    for step in job_steps:
        order = job_orders[step["step_type"]]
        update = {"order": order, "updated_at": now}
        if step["step_type"] == "decision":
            update["conditions"] = wait_for(22)
        elif step["step_type"] == "partner_multiselection":
            update["conditions"] = [{
                "action": "hide", "source_step_order": 23, "field": "decision",
                "operator": "not_equals", "value": "partner_nutzen",
            }]
        else:
            update["conditions"] = [
                {
                    "action": "auto_complete", "source_step_order": 23,
                    "field": "decision", "operator": "equals", "value": "selbst",
                },
                {
                    "action": "hide", "source_step_order": 23, "field": "decision",
                    "operator": "empty", "value": "",
                },
            ]
        await db.steps.update_one({"_id": step["_id"]}, {"$set": update})
        await db.user_progress.update_many(
            {"step_id": str(step["_id"])}, {"$set": {"step_order": order}}
        )

    new_stages = (
        ("Vorbereitungskurs Kenntnisprüfung", 15, 14, "Pflege Vorbereitungskurs Kenntnisprüfung"),
        ("Kenntnisprüfung", 19, 18, "Pflege Kenntnisprüfung"),
    )
    inserted = []
    for name, order, previous, tag in new_stages:
        existing = await db.steps.find_one({"survey_id": survey_id, "title": name})
        if existing:
            continue
        docs = stage_documents(survey_id, name, order, previous, tag, now)
        result = await db.steps.insert_many(docs, ordered=True)
        inserted.extend(zip(result.inserted_ids, docs))

    # Keep Pflege partner matching functional after the renamed/new tags.
    async for partner in db.partners.find({
        "$or": [
            {"tags": {"$regex": "^Pflege (Approbation|Sprachprüfung)$"}},
            {"category": {"$regex": "^Pflege (Approbation|Sprachprüfung)$"}},
        ]
    }):
        normalized = replace_terms(deepcopy(partner))
        normalized.pop("_id", None)
        tags = normalized.get("tags") or []
        if "Pflege Fachsprachenprüfung" in tags:
            for tag in ("Pflege Vorbereitungskurs Kenntnisprüfung", "Pflege Kenntnisprüfung"):
                if tag not in tags:
                    tags.append(tag)
        normalized["tags"] = tags
        normalized["updated_at"] = now
        await db.partners.replace_one({"_id": partner["_id"]}, normalized)

    # Future-proof the migration for Pflege users even though the current
    # baseline contains none yet.
    users = await db.users.find({"role": "user", "survey_id": survey_id}, {"_id": 1}).to_list(100000)
    if inserted and users:
        rows = []
        for user in users:
            for step_id, step in inserted:
                rows.append({
                    "user_id": str(user["_id"]), "step_id": str(step_id),
                    "survey_id": survey_id, "step_order": step["order"],
                    "status": "pending", "data": {}, "files": [], "updated_at": now,
                })
        if rows:
            await db.user_progress.insert_many(rows, ordered=False)

    ordered = await db.steps.find(
        {"survey_id": survey_id}, {"title": 1, "order": 1}
    ).sort("order", 1).to_list(100)
    orders = [step["order"] for step in ordered]
    if orders != list(range(1, 26)):
        raise RuntimeError(f"Unexpected Pflege order chain: {orders}")
    if any("Approbation" in step["title"] or "Gleichwertigkeits" in step["title"] for step in ordered):
        raise RuntimeError("Legacy Pflege stage terms remain")

    print("Pflege survey migration complete")
    for step in ordered:
        print(f"  {step['order']:>2}: {step['title']}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
