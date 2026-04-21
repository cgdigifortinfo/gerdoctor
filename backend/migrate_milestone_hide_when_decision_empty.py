"""Migration: add `hide` condition on every milestone step so it stays hidden
while the corresponding decision step has no value. Idempotent — skips
milestones that already carry a hide-decision-empty condition.

Run:  python3 /app/backend/migrate_milestone_hide_when_decision_empty.py
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

# Mirror BLOCK_DEFINITIONS in helpers.py: decision_order per milestone_order.
# (milestone_order -> decision_order)
MILESTONE_TO_DECISION = {
    5:  2,   # Antragstellung Approbation
    9:  6,   # Fachsprachenprüfung
    13: 10,  # Gleichwertigkeitsprüfung
    17: 14,  # Kenntnisprüfung
    20: 18,  # Jobangebote (no upload)
    24: 21,  # Weiterbildung
}


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    updated = 0
    already_ok = 0
    not_found = []
    for ms_order, dec_order in MILESTONE_TO_DECISION.items():
        ms = await db.steps.find_one({"order": ms_order, "step_type": "milestone"})
        if not ms:
            not_found.append(ms_order)
            continue
        conditions = list(ms.get("conditions") or [])

        def _has_hide_when_empty():
            for c in conditions:
                if (c.get("action") == "hide"
                    and c.get("source_step_order") == dec_order
                    and c.get("field") == "decision"
                    and c.get("operator") == "empty"):
                    return True
            return False

        if _has_hide_when_empty():
            already_ok += 1
            continue

        conditions.append({
            "action": "hide",
            "source_step_order": dec_order,
            "field": "decision",
            "operator": "empty",
            "value": "",
        })
        await db.steps.update_one({"_id": ms["_id"]}, {"$set": {"conditions": conditions}})
        print(f"  + milestone #{ms_order} ('{ms.get('title')}') → added hide-when-decision-{dec_order}-empty")
        updated += 1

    print(f"\nMigration complete. Updated: {updated}, already OK: {already_ok}, not found: {not_found}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
