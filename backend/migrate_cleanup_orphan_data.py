"""Cleanup orphan data:

1. Delete `user_progress` entries whose `user_id` belongs to a user with
   `role != 'user'` (admin/partner). These are leftovers from accounts that
   used to be doctors and were later promoted.
2. Delete `partner_submissions` whose `user_id` belongs to a non-`user`.
3. Rename data field `partner_attachments` → `partner_uploads` everywhere
   so the (single) canonical key matches the partner-completion code path
   and renders as download links in the partner dashboard.

Idempotent — safe to re-run.
Run: python3 /app/backend/migrate_cleanup_orphan_data.py
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    # --- (1) Identify non-user accounts ---
    non_user_accounts = await db.users.find(
        {"role": {"$ne": "user"}}, {"_id": 1, "email": 1, "role": 1}
    ).to_list(500)
    non_user_ids = [str(u["_id"]) for u in non_user_accounts]
    print(f"Found {len(non_user_ids)} non-user accounts (admin/partner).")

    # --- (2) Delete orphan user_progress entries ---
    progress_res = await db.user_progress.delete_many({"user_id": {"$in": non_user_ids}})
    print(f"Removed {progress_res.deleted_count} orphan user_progress entries.")

    # --- (3) Delete orphan partner_submissions ---
    sub_res = await db.partner_submissions.delete_many({"user_id": {"$in": non_user_ids}})
    print(f"Removed {sub_res.deleted_count} orphan partner_submissions entries.")

    # --- (4) Migrate partner_attachments → partner_uploads ---
    rename_count = 0
    async for prog in db.user_progress.find({"data.partner_attachments": {"$exists": True}}):
        data = prog.get("data") or {}
        if "partner_attachments" not in data:
            continue
        # If both keys exist, merge (preserve newest)
        existing = data.get("partner_uploads") or []
        attachments = data.get("partner_attachments") or []
        merged = existing + [a for a in attachments if a not in existing]
        await db.user_progress.update_one(
            {"_id": prog["_id"]},
            {"$set": {"data.partner_uploads": merged}, "$unset": {"data.partner_attachments": ""}},
        )
        rename_count += 1
    print(f"Renamed partner_attachments → partner_uploads on {rename_count} progress entries.")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
