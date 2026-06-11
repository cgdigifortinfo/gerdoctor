"""Seed data expected by the local backend/E2E test suite.

This is intentionally separate from the product/demo seeds.  It fills gaps in
older tests that expect fixed partner accounts and a large partner-insights data
set, while keeping the current Survey v2 step structure intact.

Run: cd /app/backend && python seed_test_fixtures.py
"""
import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import Any

import bcrypt
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def get_or_create_partner(db, name: str, fields: dict[str, Any]) -> dict[str, Any]:
    existing = await db.partners.find_one({"name": name})
    payload = {
        "name": name,
        "is_active": True,
        "created_at": fields.get("created_at", now_iso()),
        **fields,
    }
    if existing:
        await db.partners.update_one({"_id": existing["_id"]}, {"$set": payload})
        return await db.partners.find_one({"_id": existing["_id"]})
    result = await db.partners.insert_one(payload)
    return await db.partners.find_one({"_id": result.inserted_id})


async def get_or_create_user(db, email: str, name: str, role: str, password: str,
                             extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "email": email.lower(),
        "name": name,
        "role": role,
        "password_hash": hash_password(password),
        "profile": {},
        "created_at": now_iso(),
        **(extra or {}),
    }
    existing = await db.users.find_one({"email": email.lower()})
    if existing:
        await db.users.update_one({"_id": existing["_id"]}, {"$set": payload})
        return await db.users.find_one({"_id": existing["_id"]})
    result = await db.users.insert_one(payload)
    return await db.users.find_one({"_id": result.inserted_id})


async def ensure_progress(db, user_id: str, step_id: str, order: int,
                          status: str = "pending", data: dict[str, Any] | None = None,
                          days_ago: int = 0) -> None:
    when = iso_days_ago(days_ago)
    payload: dict[str, Any] = {
        "user_id": user_id,
        "step_id": step_id,
        "step_order": order,
        "status": status,
        "data": data or {},
        "updated_at": when,
    }
    if status == "completed":
        payload["completed_at"] = when
    await db.user_progress.update_one(
        {"user_id": user_id, "step_id": step_id},
        {"$set": payload, "$setOnInsert": {"created_at": when}},
        upsert=True,
    )


async def ensure_all_pending_progress(db, user_id: str, steps: list[dict[str, Any]]) -> None:
    for step in steps:
        await ensure_progress(db, user_id, str(step["_id"]), step["order"])


async def ensure_submission(db, user: dict[str, Any], partner: dict[str, Any],
                            data: dict[str, Any] | None = None,
                            days_ago: int = 1,
                            completed: bool = False) -> None:
    user_id = str(user["_id"])
    partner_id = str(partner["_id"])
    payload = {
        "id": f"fixture-{user_id}-{partner_id}",
        "user_id": user_id,
        "partner_id": partner_id,
        "user_email": user["email"],
        "user_name": user["name"],
        "data": data or {},
        "status": "submitted",
        "partner_work_completed": completed,
        "created_at": iso_days_ago(days_ago),
        "updated_at": now_iso(),
    }
    if completed:
        payload["completed_at"] = iso_days_ago(max(days_ago - 1, 0))
    await db.partner_submissions.update_one(
        {"user_id": user_id, "partner_id": partner_id},
        {"$set": payload},
        upsert=True,
    )


async def seed_fixed_partner_accounts(db, steps: list[dict[str, Any]]) -> None:
    ils = await get_or_create_partner(db, "ILS", {
        "description": "Test fixture partner for API role and partner dashboard tests.",
        "category": "Antragstellung",
        "tags": ["Berlin", "Kardiologie", "Innere Medizin", "Bayern", "Antragstellung Approbation"],
        "website": "https://example.com/ils",
        "contact_email": "partner-example@chrizz1001.de",
        "logo_url": "https://example.com/ils.png",
    })
    ils_user = await get_or_create_user(
        db,
        "partner-example@chrizz1001.de",
        "Partner Example",
        "partner",
        "Partner123!",
        {"partner_id": str(ils["_id"])},
    )
    await db.partners.update_one(
        {"_id": ils["_id"]},
        {"$addToSet": {"linked_user_ids": str(ils_user["_id"])}, "$set": {"user_id": str(ils_user["_id"])}},
    )

    praxis = await get_or_create_partner(db, "Praxis Test Empfang", {
        "description": "Praxis fixture for partner self-service tests.",
        "category": "Praxis",
        "tags": ["Praxis", "Berlin", "Allgemeinmedizin"],
        "website": "https://example.com/praxis",
        "contact_email": "empfang@chrizz1001.de",
        "logo_url": "https://example.com/praxis.png",
    })
    praxis_user = await get_or_create_user(
        db,
        "empfang@chrizz1001.de",
        "Empfang Praxis",
        "partner",
        "Partner123!",
        {"partner_id": str(praxis["_id"])},
    )
    await db.partners.update_one(
        {"_id": praxis["_id"]},
        {"$addToSet": {"linked_user_ids": str(praxis_user["_id"])}, "$set": {"user_id": str(praxis_user["_id"])}},
    )

    step1 = next(s for s in steps if s["order"] == 1)
    step2 = next(s for s in steps if s["order"] == 2)
    for email, partner, name in [
        ("fixture-ils-user@chrizz1001.de", ils, "Fixture ILS User"),
        ("fixture-praxis-user@chrizz1001.de", praxis, "Fixture Praxis User"),
    ]:
        user = await get_or_create_user(db, email, name, "user", "Demo123!")
        await ensure_all_pending_progress(db, str(user["_id"]), steps)
        await ensure_progress(db, str(user["_id"]), str(step1["_id"]), 1, "completed", {
            "first_name": name.split()[0],
            "name": name.split()[-1],
            "field_of_study": "Innere Medizin",
            "fachrichtung_praktiziert": "Innere Medizin",
            "fachrichtung_gewuenscht": "Kardiologie",
            "anerkennungsverfahren_bundesland": "Berlin",
        })
        await ensure_progress(db, str(user["_id"]), str(step2["_id"]), 2, "completed", {"decision": "selber"})
        await ensure_submission(db, user, partner, {
            "field_of_study": "Innere Medizin",
            "bundesland": "Berlin",
            "source": "fixture",
        }, completed=False)


async def seed_fia_insights_volume(db, steps: list[dict[str, Any]]) -> None:
    fia = await db.partners.find_one({"name": "FIA Academy"})
    if not fia:
        fia = await get_or_create_partner(db, "FIA Academy", {
            "description": "FIA Academy fixture partner.",
            "category": "Kenntnisprüfung",
            "tags": ["Kenntnisprüfung", "Fachsprachenprüfung", "Berlin", "Innere Medizin"],
            "contact_email": "partner-fia-academy@chrizz1001.de",
        })
    else:
        tags = set(fia.get("tags") or [])
        tags.update(["Kenntnisprüfung", "Fachsprachenprüfung", "Berlin", "Innere Medizin"])
        await db.partners.update_one({"_id": fia["_id"]}, {"$set": {"tags": sorted(tags)}})
        fia = await db.partners.find_one({"_id": fia["_id"]})

    fia_user = await get_or_create_user(
        db,
        "partner-fia-academy@chrizz1001.de",
        "Partner: FIA Academy",
        "partner",
        "Partner123!",
        {"partner_id": str(fia["_id"])},
    )
    await db.partners.update_one(
        {"_id": fia["_id"]},
        {"$addToSet": {"linked_user_ids": str(fia_user["_id"])}, "$set": {"user_id": str(fia_user["_id"])}},
    )

    step1 = next(s for s in steps if s["order"] == 1)
    step2 = next(s for s in steps if s["order"] == 2)
    fields = ["Innere Medizin", "Kardiologie", "Chirurgie", "Pädiatrie"]
    states = ["Berlin", "Bayern", "Hessen", "Hamburg", "Nordrhein-Westfalen"]
    for i in range(166):
        field = fields[i % len(fields)]
        state = states[i % len(states)]
        user = await get_or_create_user(
            db,
            f"fixture-fia-{i:03d}@chrizz1001.de",
            f"Fixture FIA {i:03d}",
            "user",
            "Demo123!",
        )
        uid = str(user["_id"])
        await ensure_all_pending_progress(db, uid, steps)
        await ensure_progress(db, uid, str(step1["_id"]), 1, "completed", {
            "first_name": "Fixture",
            "name": f"FIA {i:03d}",
            "field_of_study": field,
            "fachrichtung_praktiziert": field,
            "fachrichtung_gewuenscht": field,
            "anerkennungsverfahren_bundesland": state,
        }, days_ago=i % 25)
        await ensure_progress(db, uid, str(step2["_id"]), 2, "completed", {"decision": "selber"}, days_ago=i % 25)
        await ensure_submission(db, user, fia, {
            "field_of_study": field,
            "bundesland": state,
            "source": "fixture-fia-volume",
        }, days_ago=i % 25, completed=False)


async def seed_cms_box_translations(db) -> None:
    en_boxes = {
        "box1_title": "Guided applications",
        "box1_description": "Keep each licensing step structured and visible.",
        "box2_title": "Trusted partners",
        "box2_description": "Connect with services that support your journey.",
        "box3_title": "Progress tracking",
        "box3_description": "See what is done, pending, and waiting for review.",
    }
    de_boxes = {
        "box1_title": "Geführte Antragstellung",
        "box1_description": "Behalte jeden Schritt zur Anerkennung im Blick.",
        "box2_title": "Geprüfte Partner",
        "box2_description": "Finde passende Unterstützung für deinen Weg.",
        "box3_title": "Fortschritt im Blick",
        "box3_description": "Sieh, was erledigt ist und was noch aussteht.",
    }
    await db.cms_content.update_one(
        {"section": "home"},
        {
            "$set": {
                **{f"content.{k}": v for k, v in de_boxes.items()},
                **{f"translations.en.{k}": v for k, v in en_boxes.items()},
                "updated_at": now_iso(),
            },
            "$setOnInsert": {"section": "home", "created_at": now_iso()},
        },
        upsert=True,
    )


async def seed_admin_test_password(db) -> None:
    await db.users.update_one(
        {"email": "admin@example.com"},
        {"$set": {"password_hash": hash_password("Admin123!"), "role": "admin", "name": "Admin"}},
        upsert=False,
    )


async def run() -> None:
    client = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    steps = await db.steps.find({"is_active": True}).sort("order", 1).to_list(200)
    if not steps:
        raise RuntimeError("No active steps found. Run seed_survey_v2.py first.")

    await seed_admin_test_password(db)
    await seed_fixed_partner_accounts(db, steps)
    await seed_fia_insights_volume(db, steps)
    await seed_cms_box_translations(db)
    await db.login_attempts.delete_many({})

    print("Seeded test fixtures:")
    print(f"  users: {await db.users.count_documents({})}")
    print(f"  partners: {await db.partners.count_documents({})}")
    print(f"  partner_submissions: {await db.partner_submissions.count_documents({})}")
    print(f"  FIA submissions: {await db.partner_submissions.count_documents({'partner_id': str((await db.partners.find_one({'name': 'FIA Academy'}))['_id'])})}")
    client.close()


if __name__ == "__main__":
    asyncio.run(run())
