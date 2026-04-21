"""
Migration: merge duplicate partner orgs.

The seed produced two "IQB" partners that differ only in umlaut usage:
  - "IQB Pruefungszentrum" (no umlaut, category=Gleichwertigkeitspruefung)
  - "IQB Prüfungszentrum"  (umlaut,    category=Gleichwertigkeitsprüfung)

Both serve the exact same purpose in the journey. Step 12's filter_tag is
"Gleichwertigkeitsprüfung" (umlaut), so the UI only ever shows the umlaut
variant — but user picks/submissions for users who came in via earlier data
or older seeds could be split between the two, causing partner dashboards to
miss users.

This script merges the no-umlaut variant INTO the umlaut variant (keeper):
  - partner_submissions.partner_id  →  keeper id
  - user_progress.data.selected_partner_id → keeper id (if equal to victim)
  - user_progress.data.selected_partner_ids list entries → keeper id
  - partners[keeper].linked_user_ids  ← union(both)
  - users[role=partner, partner_id=victim].partner_id → keeper id
  - delete the victim

Idempotent — safe to run multiple times.

Run: cd /app/backend && python3 merge_duplicate_iqb_partners.py
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

KEEPER_NAME = "IQB Prüfungszentrum"   # umlaut variant → kept
VICTIM_NAME = "IQB Pruefungszentrum"  # no-umlaut variant → merged away


async def run() -> int:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    keeper = await db.partners.find_one({"name": KEEPER_NAME})
    victim = await db.partners.find_one({"name": VICTIM_NAME})

    if not victim:
        print(f"✓ No '{VICTIM_NAME}' partner found — nothing to merge (already idempotent).")
        client.close()
        return 0
    if not keeper:
        print(f"!! Keeper '{KEEPER_NAME}' not found — aborting to avoid data loss.")
        client.close()
        return 2

    keeper_id = str(keeper["_id"])
    victim_id = str(victim["_id"])
    print(f"Merging '{VICTIM_NAME}' ({victim_id})  →  '{KEEPER_NAME}' ({keeper_id})")

    # 1. Re-point partner_submissions
    n_subs = (await db.partner_submissions.update_many(
        {"partner_id": victim_id},
        {"$set": {"partner_id": keeper_id}},
    )).modified_count
    print(f"  • {n_subs} partner_submissions re-pointed")

    # 2. Re-point user_progress.data.selected_partner_id
    n_prog = (await db.user_progress.update_many(
        {"data.selected_partner_id": victim_id},
        {"$set": {"data.selected_partner_id": keeper_id}},
    )).modified_count
    print(f"  • {n_prog} user_progress rows re-pointed (selected_partner_id)")

    # 3. Re-point user_progress.data.selected_partner_ids[] list entries
    n_multi = 0
    async for p in db.user_progress.find({"data.selected_partner_ids": victim_id}):
        ids = p.get("data", {}).get("selected_partner_ids", []) or []
        new_ids = [keeper_id if x == victim_id else x for x in ids]
        # Deduplicate (in case user already had keeper too)
        seen = []
        for x in new_ids:
            if x not in seen:
                seen.append(x)
        await db.user_progress.update_one(
            {"_id": p["_id"]},
            {"$set": {"data.selected_partner_ids": seen}},
        )
        n_multi += 1
    print(f"  • {n_multi} user_progress rows re-pointed (selected_partner_ids list)")

    # 4. Re-point partner-role users whose partner_id points to victim
    n_users = (await db.users.update_many(
        {"partner_id": victim_id},
        {"$set": {"partner_id": keeper_id}},
    )).modified_count
    print(f"  • {n_users} partner-role users re-pointed")

    # 5. Union linked_user_ids on keeper
    victim_linked = set(victim.get("linked_user_ids", []) or [])
    keeper_linked = set(keeper.get("linked_user_ids", []) or [])
    union = sorted(keeper_linked | victim_linked)
    await db.partners.update_one(
        {"_id": keeper["_id"]},
        {"$set": {"linked_user_ids": union}},
    )
    print(f"  • linked_user_ids union = {len(union)} (keeper had {len(keeper_linked)}, victim had {len(victim_linked)})")

    # 6. Delete the victim partner org
    await db.partners.delete_one({"_id": victim["_id"]})
    print(f"  ✓ Victim partner org deleted")

    client.close()
    print("\n✓ Merge complete.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
