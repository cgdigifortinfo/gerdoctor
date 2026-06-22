"""Make the current survey flow a linear visible chain.

Before this migration the later theme blocks were visible but blocked as soon as
the user reached the beginning of the journey, and after the Approbation
milestone all later blocks became available in parallel. This adds `hide`
conditions and chains every block to the previous milestone:

  7  Fachsprachenprüfung       waits for 6
  11 Gleichwertigkeitsprüfung  waits for 10
  15 Kenntnisprüfung           waits for 14
  19 Jobangebote               waits for 18
  22 Weiterbildung             waits for 21
"""
import asyncio
import os
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient


CHAIN = {
    7: 6,
    11: 10,
    15: 14,
    19: 18,
    22: 21,
}


def block_condition(source_order: int) -> dict:
    return {
        "action": "block",
        "source_step_order": source_order,
        "field": "",
        "operator": "status_not",
        "value": "completed",
        "message": "Bitte schließen Sie zuerst den vorherigen Meilenstein ab.",
    }


def hide_condition(source_order: int) -> dict:
    return {
        "action": "hide",
        "source_step_order": source_order,
        "field": "",
        "operator": "status_not",
        "value": "completed",
    }


async def run():
    client = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    now = datetime.now(timezone.utc).isoformat()

    updated = 0
    for step_order, source_order in CHAIN.items():
        step = await db.steps.find_one({"order": step_order})
        if not step:
            print(f"Step order {step_order} not found, skipping")
            continue

        conditions = [
            c for c in (step.get("conditions") or [])
            if not (
                c.get("action") in {"block", "hide"}
                and c.get("operator") == "status_not"
                and c.get("value") == "completed"
                and not c.get("field")
            )
        ]
        conditions.extend([block_condition(source_order), hide_condition(source_order)])
        await db.steps.update_one(
            {"_id": step["_id"]},
            {"$set": {"conditions": conditions, "updated_at": now}},
        )
        updated += 1
        print(f"Updated step {step_order}: now chained to milestone {source_order}")

    print(f"Done. Updated {updated} steps.")
    client.close()


if __name__ == "__main__":
    asyncio.run(run())
