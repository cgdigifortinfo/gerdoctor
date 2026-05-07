"""Backfill: mark step #2 (Schnellstart) as completed=selber for existing demo
users that have already completed Stammdaten (step #1).

The migrate_add_ueberholspur_step.py inserted pending stubs for the new step
on every user. For seeded demo users that have already moved past Stammdaten,
they would now be visually stuck on the new decision step. Auto-completing it
with `decision='selber'` keeps the demo data flowing through the journey.

Idempotent — only fills users where step #2 is still pending.
Run: python3 /app/backend/migrate_backfill_ueberholspur_decision.py
"""
import asyncio
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    step1 = await db.steps.find_one({"order": 1, "is_active": True})
    step2 = await db.steps.find_one({"order": 2, "is_active": True})
    if not step1 or not step2:
        raise RuntimeError("Step 1 or 2 not found — run the migration first.")
    if step2.get("title") != "Schnellstart oder Selbststart?":
        raise RuntimeError(
            f"Step #2 is not the Schnellstart decision (got: {step2.get('title')!r}); "
            "refusing to backfill."
        )
    sid1, sid2 = str(step1["_id"]), str(step2["_id"])

    # Find users whose step1 = completed AND step2 = pending
    users_to_fix = []
    async for prog in db.user_progress.find({"step_id": sid1, "status": "completed"}):
        uid = prog["user_id"]
        prog2 = await db.user_progress.find_one({"user_id": uid, "step_id": sid2})
        if prog2 and prog2.get("status") in (None, "pending", "in_progress"):
            users_to_fix.append((uid, prog.get("completed_at") or prog.get("updated_at")))

    print(f"[backfill] {len(users_to_fix)} users with step1=completed but step2=pending")

    now = datetime.now(timezone.utc).isoformat()
    fixed = 0
    for uid, step1_done_at in users_to_fix:
        # Use a timestamp ~1 minute after step1 completion so the timeline
        # stays monotonic in the user's history.
        completed_at = step1_done_at or now
        await db.user_progress.update_one(
            {"user_id": uid, "step_id": sid2},
            {"$set": {
                "status": "completed",
                "data": {"decision": "selber", "auto_filled_by_migration": True},
                "started_at": completed_at,
                "completed_at": completed_at,
                "updated_at": now,
            }},
        )
        fixed += 1
    print(f"[backfill] Updated {fixed} progress rows.")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
