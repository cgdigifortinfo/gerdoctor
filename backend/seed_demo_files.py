"""Add real placeholder upload files to existing demo users.

For each demo user (`demoNNN-*@chrizz1001.de`) we look at their progress and:
  • For every upload-step (form with documents) that has a non-empty data.documents
    array, replace the fake file_id refs with REAL files inserted into db.files
    AND uploaded as 1x1 red PNG to object storage.
  • For every milestone the partner has completed via the partner side, add a
    "partner_verification.png" attachment as well so admins/users see proof.

Run: python3 /app/backend/seed_demo_files.py
"""
import asyncio
import base64
import os
import uuid
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
import sys
sys.path.insert(0, "/app/backend")
from helpers import put_object, APP_NAME

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]


# 1×1 red PNG (8-bit RGB) — pre-encoded so seeding is deterministic and fast.
RED_1x1_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGA"
    "hKmMIQAAAABJRU5ErkJggg=="
)
RED_1x1_PNG_BYTES = base64.b64decode(RED_1x1_PNG_B64)


async def upload_placeholder(user_id: str, filename: str, kind: str) -> dict:
    """Persist a file in db.files + storage. Returns the document so the caller
    can reference {file_id, filename} in step-progress data."""
    file_id = str(uuid.uuid4())
    ext = "png"
    path = f"{APP_NAME}/uploads/{user_id}/{file_id}.{ext}"
    res = put_object(path, RED_1x1_PNG_BYTES, "image/png")
    file_doc = {
        "id": file_id,
        "user_id": str(user_id),
        "storage_path": res["path"],
        "original_filename": filename,
        "content_type": "image/png",
        "size": res.get("size", len(RED_1x1_PNG_BYTES)),
        "is_deleted": False,
        "kind": kind,  # 'user_upload' or 'partner_verification'
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.files.insert_one(file_doc)
    return {"file_id": file_id, "filename": filename}


# Map upload-step orders → human-friendly placeholder name (German)
UPLOAD_STEP_FILENAMES = {
    3:  "approbations_dokumente.png",
    7:  "fachsprachenpruefung_dokumente.png",
    11: "gleichwertigkeitspruefung_dokumente.png",
    15: "kenntnispruefung_dokumente.png",
    22: "weiterbildung_dokumente.png",
}
MILESTONE_PARTNER_FILENAMES = {
    5:  "partner_bestaetigung_approbation.png",
    9:  "partner_bestaetigung_fachsprache.png",
    13: "partner_bestaetigung_gleichwertigkeit.png",
    17: "partner_bestaetigung_kenntnispruefung.png",
    20: "partner_bestaetigung_jobangebote.png",
    24: "partner_bestaetigung_weiterbildung.png",
}


async def main():
    users = await db.users.find({"role": "user"}, {"_id": 1, "email": 1}).to_list(2000)
    print(f"Processing {len(users)} demo users…")

    user_uploads = 0
    partner_uploads = 0

    for u in users:
        uid = str(u["_id"])
        # Walk all progress entries for this user
        async for prog in db.user_progress.find({"user_id": uid}):
            so = prog.get("step_order")
            data = prog.get("data") or {}

            # ---------- USER upload steps (3,7,11,15,22) ----------
            if so in UPLOAD_STEP_FILENAMES and prog.get("status") == "completed":
                docs = data.get("documents") or []
                # Skip if already has real file_ids (uuids look like uuids)
                if docs and any(len(d.get("file_id", "")) == 36 for d in docs):
                    continue
                placeholder = await upload_placeholder(uid, UPLOAD_STEP_FILENAMES[so], "user_upload")
                placeholder["uploaded_at"] = datetime.now(timezone.utc).isoformat()
                data["documents"] = [placeholder]
                await db.user_progress.update_one({"_id": prog["_id"]}, {"$set": {"data": data}})
                user_uploads += 1

            # ---------- PARTNER upload at milestone (5,9,13,17,20,24) ----------
            elif so in MILESTONE_PARTNER_FILENAMES and prog.get("status") == "completed":
                completed_by = data.get("completed_by")
                if completed_by != "partner":
                    continue
                if data.get("partner_attachments"):
                    continue  # already seeded
                placeholder = await upload_placeholder(uid, MILESTONE_PARTNER_FILENAMES[so], "partner_verification")
                placeholder["uploaded_at"] = datetime.now(timezone.utc).isoformat()
                data["partner_attachments"] = [placeholder]
                await db.user_progress.update_one({"_id": prog["_id"]}, {"$set": {"data": data}})
                partner_uploads += 1

    print(f"  user uploads added:    {user_uploads}")
    print(f"  partner uploads added: {partner_uploads}")
    print(f"  total db.files docs:   {await db.files.count_documents({})}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
