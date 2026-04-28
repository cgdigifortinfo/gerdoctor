"""Repair user_progress data structure + remove orphan duplicate steps.

Problems addressed:

1. **Orphan duplicate "Persönliche Daten" steps** (order > 25) created by
   `test_template_from_step_and_apply_and_cleanup` test failures whose cleanup
   block never ran. We delete them and any progress/history references.

2. **Missing `step_order` on progress rows**: `/api/auth/register` historically
   inserted pending rows without `step_order`. Backfill it from the step's
   current `order` value.

3. **Missing pending progress rows**: The 100-demo-user seed only inserts
   progress for steps the user actually touched, leaving gaps. The progress
   collection should hold one row per (user, active step) so visibility +
   ETA calculations behave consistently. We insert a `pending` row for every
   missing (user, step) pair.

4. **Duplicate progress rows for same (user_id, step_id)**: dedupe and keep
   the most recent.

Idempotent — safe to re-run.
Run: python3 /app/backend/migrate_repair_progress_data.py
"""
import asyncio
import os
from datetime import datetime, timezone
from collections import defaultdict
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    # ---- (1) Drop orphan duplicate Persönliche Daten steps (order > 25) ----
    orphan_steps = await db.steps.find({
        "is_active": True,
        "order": {"$gt": 25},
        "title": "Persönliche Daten",
    }).to_list(50)
    orphan_step_ids = [str(s["_id"]) for s in orphan_steps]
    if orphan_step_ids:
        progr = await db.user_progress.delete_many({"step_id": {"$in": orphan_step_ids}})
        hist = await db.progress_history.delete_many({"step_id": {"$in": orphan_step_ids}})
        steps_del = await db.steps.delete_many({"_id": {"$in": [s["_id"] for s in orphan_steps]}})
        print(f"[1] Removed {steps_del.deleted_count} orphan duplicate steps "
              f"({progr.deleted_count} progress rows, {hist.deleted_count} history rows).")
    else:
        print("[1] No orphan duplicate steps.")

    # Build a lookup of every active step → order
    active_steps = await db.steps.find({"is_active": True}, {"order": 1}).to_list(100)
    step_order_by_id = {str(s["_id"]): s.get("order") for s in active_steps}
    active_step_ids = set(step_order_by_id.keys())
    print(f"    active step count after cleanup: {len(active_step_ids)}")

    # ---- (2) Backfill step_order on progress rows ----
    backfilled = 0
    async for prog in db.user_progress.find({
        "$or": [{"step_order": {"$exists": False}}, {"step_order": None}],
    }):
        sid = prog.get("step_id")
        if sid in step_order_by_id:
            await db.user_progress.update_one(
                {"_id": prog["_id"]},
                {"$set": {"step_order": step_order_by_id[sid]}},
            )
            backfilled += 1
    print(f"[2] Backfilled step_order on {backfilled} progress rows.")

    # ---- (3) Drop progress rows referencing inactive/deleted steps ----
    stale = await db.user_progress.delete_many({"step_id": {"$nin": list(active_step_ids)}})
    print(f"[3] Removed {stale.deleted_count} progress rows referencing non-active step ids.")

    # ---- (4) Dedupe + ensure 1 row per (user, step) ----
    # Collect everything in memory once — fits easily for ~150 users * 25 steps.
    rows_by_key: dict[tuple[str, str], list] = defaultdict(list)
    async for prog in db.user_progress.find({}):
        key = (prog["user_id"], prog["step_id"])
        rows_by_key[key].append(prog)

    duplicates_removed = 0
    for key, rows in rows_by_key.items():
        if len(rows) > 1:
            # Keep the latest by updated_at (or _id), drop the rest.
            rows.sort(key=lambda r: r.get("updated_at") or r.get("created_at") or "")
            keep = rows[-1]
            for stale_row in rows[:-1]:
                await db.user_progress.delete_one({"_id": stale_row["_id"]})
                duplicates_removed += 1
    print(f"[4] Removed {duplicates_removed} duplicate progress rows.")

    # ---- (5) Insert pending stubs for every (user, missing step) pair ----
    users = await db.users.find({"role": "user"}, {"_id": 1, "created_at": 1}).to_list(2000)
    inserted = 0
    now = datetime.now(timezone.utc).isoformat()
    for u in users:
        uid = str(u["_id"])
        seen_step_ids = {key[1] for key in rows_by_key if key[0] == uid}
        # also collect the live ones we just deduplicated
        if uid in {k[0] for k in rows_by_key}:
            seen_step_ids = {k[1] for k in rows_by_key if k[0] == uid}
        # actually re-fetch fresh to be safe
        live = await db.user_progress.find({"user_id": uid}, {"step_id": 1}).to_list(100)
        seen_step_ids = {p["step_id"] for p in live}
        missing = active_step_ids - seen_step_ids
        if not missing:
            continue
        rows = [{
            "user_id": uid,
            "step_id": sid,
            "step_order": step_order_by_id[sid],
            "status": "pending",
            "data": {},
            "created_at": u.get("created_at") or now,
            "updated_at": now,
        } for sid in missing]
        if rows:
            await db.user_progress.insert_many(rows)
            inserted += len(rows)
    print(f"[5] Inserted {inserted} missing pending stubs.")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
