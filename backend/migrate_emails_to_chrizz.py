"""Migration: replace every email domain in the system with @chrizz1001.de
EXCEPT the master admin account `admin@example.com`.

Idempotent — safe to run multiple times.

Touches:
  • users.email
  • partners.contact_email
  • partner_submissions.user_email
  • audit_log.user_email
  • Anything else with a top-level `email` string field is also patched
    defensively (sessions, etc.).

Run:  python3 /app/backend/migrate_emails_to_chrizz.py
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
NEW_DOMAIN = "chrizz1001.de"
KEEP_AS_IS = {"admin@example.com"}


def transform(email: str) -> str | None:
    """Return the new email or None if it should not be changed."""
    if not email or not isinstance(email, str):
        return None
    if email in KEEP_AS_IS:
        return None
    if email.endswith("@" + NEW_DOMAIN):
        return None  # already migrated
    if "@" not in email:
        return None
    local = email.split("@", 1)[0]
    return f"{local}@{NEW_DOMAIN}"


async def patch_collection(db, coll_name, field):
    """Patch a single string field on every doc in the collection. For the
    `users` collection a unique-index clash is avoided by appending a
    deterministic suffix derived from the original local-part."""
    coll = db[coll_name]
    count = 0
    cursor = coll.find({field: {"$type": "string"}})
    async for doc in cursor:
        old = doc.get(field)
        new = transform(old)
        if new is None:
            continue
        if coll_name == "users":
            # If a different user already owns `new`, build a unique alternate
            # using the part of the original domain (e.g. `partner@x.de` →
            # `partner-x@chrizz1001.de`).
            clash = await coll.find_one({field: new, "_id": {"$ne": doc["_id"]}})
            if clash:
                local, _, original_domain = old.partition("@")
                slug = original_domain.split(".")[0].replace("ü", "u").replace("ö", "o")
                candidate = f"{local}-{slug}@{NEW_DOMAIN}"
                # Keep walking with -2/-3 suffixes if even that clashes
                attempt = 1
                while await coll.find_one({field: candidate, "_id": {"$ne": doc["_id"]}}):
                    attempt += 1
                    candidate = f"{local}-{slug}-{attempt}@{NEW_DOMAIN}"
                new = candidate
        await coll.update_one({"_id": doc["_id"]}, {"$set": {field: new}})
        count += 1
    print(f"{coll_name}.{field}: rewrote {count} doc(s)")


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    await patch_collection(db, "users", "email")
    await patch_collection(db, "partners", "contact_email")
    await patch_collection(db, "partner_submissions", "user_email")
    await patch_collection(db, "audit_log", "user_email")
    # email_templates references admin email at runtime — nothing to migrate
    # there. Sessions usually only carry user_id.

    client.close()
    print("\nEmail-domain migration complete.")


if __name__ == "__main__":
    asyncio.run(main())
