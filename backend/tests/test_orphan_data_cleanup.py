"""Regression: Orphan-data cleanup migration

Validates that:
1. No `user_progress` rows exist for non-`user` accounts (admin/partner).
2. No `partner_submissions` rows reference a non-`user` account as user_id.
3. No data field still uses the legacy key `partner_attachments` — the canonical
   key is `partner_uploads` (matches what the partner-completion code path
   produces and what PartnerDashboard renders as download links).

Run: pytest /app/backend/tests/test_orphan_data_cleanup.py -v
"""
import asyncio
import os
import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")


@pytest.fixture(scope="module")
def db():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    return client[os.environ["DB_NAME"]]


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_no_progress_for_non_user_accounts(db):
    async def _():
        non_user_ids = [
            str(u["_id"]) async for u in db.users.find(
                {"role": {"$ne": "user"}}, {"_id": 1}
            )
        ]
        cnt = await db.user_progress.count_documents({"user_id": {"$in": non_user_ids}})
        assert cnt == 0, f"Found {cnt} orphan progress entries for admin/partner users"
    run(_())


def test_no_submissions_for_non_user_accounts(db):
    async def _():
        non_user_ids = [
            str(u["_id"]) async for u in db.users.find(
                {"role": {"$ne": "user"}}, {"_id": 1}
            )
        ]
        cnt = await db.partner_submissions.count_documents(
            {"user_id": {"$in": non_user_ids}}
        )
        assert cnt == 0, f"Found {cnt} submissions referencing non-user accounts"
    run(_())


def test_no_legacy_partner_attachments_key(db):
    async def _():
        cnt = await db.user_progress.count_documents(
            {"data.partner_attachments": {"$exists": True}}
        )
        assert cnt == 0, (
            f"Found {cnt} progress entries still using legacy "
            f"`partner_attachments` key (expected: `partner_uploads`)."
        )
    run(_())


def test_partner_uploads_have_file_id(db):
    """Spot-check: every partner_uploads entry must reference a real file."""
    async def _():
        bad = []
        async for prog in db.user_progress.find(
            {"data.partner_uploads": {"$exists": True}}
        ):
            for entry in prog.get("data", {}).get("partner_uploads", []):
                fid = entry.get("file_id")
                if not fid:
                    bad.append(f"progress {prog['_id']}: missing file_id")
                    continue
                exists = await db.files.find_one({"id": fid})
                if not exists:
                    bad.append(f"progress {prog['_id']}: file_id {fid} not in db.files")
        assert not bad, "\n".join(bad[:10])
    run(_())
