"""Migration: rebrand from "GERdoctor" to "IHCA"
=================================================
Idempotent migration that:
  1. Renames every user email *@gerdoctor.de → *@ihca.de
  2. Updates the global site_settings document (logo, title, meta).
  3. Resets header/footer/password_reset email templates if they still contain
     the old branding so admins get the new copy on next page load.
  4. Patches partner.contact_email when it ends in @gerdoctor.de.

Run:  python3 /app/backend/migrate_rebrand_ihca.py
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # 1) Users
    user_count = 0
    async for u in db.users.find({"email": {"$regex": "@gerdoctor\\.de$"}}):
        new_email = u["email"].replace("@gerdoctor.de", "@ihca.de")
        # Skip if a user already exists with the renamed address (avoid clash)
        clash = await db.users.find_one({"email": new_email})
        if clash and str(clash["_id"]) != str(u["_id"]):
            print(f"  ! skip {u['email']} → {new_email} (clash with existing user)")
            continue
        await db.users.update_one({"_id": u["_id"]}, {"$set": {"email": new_email}})
        user_count += 1
    print(f"users: renamed {user_count} email(s)")

    # 2) Partners (contact_email + display strings)
    p_count = 0
    async for p in db.partners.find({"contact_email": {"$regex": "@gerdoctor\\.de$"}}):
        new_e = p["contact_email"].replace("@gerdoctor.de", "@ihca.de")
        await db.partners.update_one({"_id": p["_id"]}, {"$set": {"contact_email": new_e}})
        p_count += 1
    print(f"partners: renamed {p_count} contact_email(s)")

    # 3) Site settings — only patch fields that still match the old branding so
    # admin custom titles/colors are preserved.
    settings = await db.site_settings.find_one({"_key": "global"})
    if settings:
        patch = {}
        if settings.get("site_title") in (None, "", "GERdoctor"):
            patch["site_title"] = "IHCA"
        if settings.get("logo_text") in (None, "", "GERdoctor"):
            patch["logo_text"] = "IHCA"
        if settings.get("logo_bold_part") in (None, "", "GER"):
            patch["logo_bold_part"] = "IH"
        if settings.get("logo_light_part") in (None, "", "doctor"):
            patch["logo_light_part"] = "CA"
        if settings.get("meta_description") in (None, "", "Praktizieren in Deutschland"):
            patch["meta_description"] = "IHCA — international health connect association. Praktizieren in Deutschland."
        if patch:
            await db.site_settings.update_one({"_key": "global"}, {"$set": patch})
            print(f"site_settings: patched {list(patch.keys())}")
        else:
            print("site_settings: already on new branding (or admin-customised)")
    else:
        print("site_settings: no global doc found (will be seeded on next backend startup)")

    # 4) Email templates — reset header/footer/password_reset if they still
    # contain the old brand string. We only reset *unedited* defaults so admin
    # copy customisations survive.
    from seed_email_templates import DEFAULT_TEMPLATES  # noqa: E402
    for key in ("header", "footer", "user_password_reset"):
        tpl = await db.email_templates.find_one({"key": key})
        if not tpl:
            continue
        if "GERdoctor" in (tpl.get("body_html", "") + " " + tpl.get("subject", "")):
            d = DEFAULT_TEMPLATES[key]
            await db.email_templates.update_one(
                {"key": key},
                {"$set": {
                    "subject": d["subject"],
                    "body_html": d["body_html"],
                    "description": d["description"],
                }},
            )
            print(f"email_templates.{key}: reset to new branding")
        else:
            print(f"email_templates.{key}: kept (admin-customised or already new)")

    client.close()
    print("\nRebrand migration complete.")


if __name__ == "__main__":
    asyncio.run(main())


async def patch_cms():
    """Replace 'GERdoctor' with 'IHCA' in every CMS content translation field."""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    count = 0
    async for c in db.cms_content.find({}):
        translations = c.get("translations") or {}
        changed = False
        for lang, fields in translations.items():
            if not isinstance(fields, dict):
                continue
            for k, v in list(fields.items()):
                if isinstance(v, str) and "GERdoctor" in v:
                    fields[k] = v.replace("GERdoctor", "IHCA")
                    changed = True
        if changed:
            await db.cms_content.update_one({"_id": c["_id"]}, {"$set": {"translations": translations}})
            count += 1
    print(f"cms_content: rewrote {count} doc(s)")
    client.close()


if __name__ == "__main__":
    # also run cms patch
    asyncio.run(patch_cms())
