import asyncio
import os

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
import pytest

from slices.step_versioning.facade import (
    bind_revision_documents,
    ensure_step_version,
    insert_step_version,
    migrate_step_answer_versioning,
    revision_view,
    utc_now,
    update_step_versioned,
    write_progress_revision,
)


def test_compatibility_facade_covers_versioning_variants():
    async def scenario():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        db = client[os.environ["DB_NAME"]]
        step_id = ObjectId()
        user_id = str(ObjectId())
        try:
            step = {"_id": step_id, "survey_id": "survey", "title": "Step", "order": 1,
                    "current_version": 1, "is_deleted": False, "obsolete": True}
            await db.steps.insert_one(step.copy())
            assert "+" in utc_now()
            assert (await insert_step_version(db, step, 1, None, "create"))["version"] == 1
            assert await ensure_step_version(db, {"id": str(step_id)}) == 1
            with pytest.raises(ValueError, match="Step does not exist"):
                await ensure_step_version(db, {"id": str(ObjectId())})
            _, _, updated = await update_step_versioned(
                db, step, {"title": "Changed"}, ["obsolete"], {"role": "admin"}, "update",
            )
            assert "obsolete" not in updated
            revision = await write_progress_revision(
                db, user_id=user_id, step=updated, status="active", data={}, actor=None,
                change_type="update", extra_fields={"temporary": True}, unset_fields=["temporary"],
            )
            assert "temporary" not in revision
            assert await bind_revision_documents(db, {**revision, "data": {}}) == 0
        finally:
            await db.steps.delete_one({"_id": step_id})
            await db.step_versions.delete_many({"step_id": str(step_id)})
            await db.user_progress.delete_many({"user_id": user_id})
            await db.user_progress_revisions.delete_many({"user_id": user_id})
            client.close()

    asyncio.run(scenario())


def test_versions_answers_and_documents_remain_immutable():
    async def scenario():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        db = client[os.environ["DB_NAME"]]
        token = str(ObjectId())
        step_id = ObjectId()
        file_id = f"version-test-{token}"
        user_id = token
        try:
            step = {
                "_id": step_id, "survey_id": token, "title": "Original", "description": "",
                "order": 1, "step_type": "form", "fields": [{
                    "name": "legacy_field", "label": "Historische Bezeichnung", "field_type": "text",
                }], "is_active": True,
                "is_deleted": False, "current_version": 1,
            }
            await db.steps.insert_one(step.copy())
            await db.files.insert_one({"id": file_id, "user_id": user_id, "filename": "original.pdf"})

            first = await write_progress_revision(
                db, user_id=user_id, step=step, status="completed",
                data={"legacy_field": "bleibt erhalten", "documents": [{"file_id": file_id, "filename": "original.pdf"}]},
                actor={"role": "user"}, change_type="user_update",
            )
            before, after, updated = await update_step_versioned(
                db, step, {"title": "Changed", "fields": []}, [], {"role": "admin"}, "update",
            )
            second = await write_progress_revision(
                db, user_id=user_id, step=updated, status="completed", data={"answer": "new"},
                actor={"role": "user"}, change_type="user_update",
            )

            assert (before, after) == (1, 2)
            assert first["revision"] == 1 and first["step_version"] == 1
            assert second["revision"] == 2 and second["step_version"] == 2
            version_one = await db.step_versions.find_one({"step_id": str(step_id), "version": 1})
            assert version_one["snapshot"]["title"] == "Original"
            revision_one = await db.user_progress_revisions.find_one({"user_id": user_id, "step_id": str(step_id), "revision": 1})
            assert revision_one["data"]["documents"][0]["file_id"] == file_id
            assert await db.document_bindings.find_one({"file_id": file_id, "step_version": 1, "progress_revision": 1})
            assert (await db.files.find_one({"id": file_id}))["historical_protected"] is True

            views = await revision_view(db, user_id)
            historical = next(row for row in views if row["revision"] == 1)
            assert historical["configuration_changed"] is True
            assert historical["step_title"] == "Original"
            assert historical["removed_field_names"] == ["legacy_field"]
            historical_field = next(field for field in historical["step_snapshot"]["fields"] if field["name"] == "legacy_field")
            assert historical_field["label"] == "Historische Bezeichnung"
            assert historical["data"]["legacy_field"] == "bleibt erhalten"

            _, delete_version, deleted = await update_step_versioned(
                db, updated, {"is_deleted": True, "is_active": False}, [], {"role": "admin"}, "delete",
            )
            assert delete_version == 3 and deleted["is_deleted"] is True
            assert await db.user_progress.find_one({"user_id": user_id, "step_id": str(step_id)})
            assert await db.user_progress_revisions.count_documents({"user_id": user_id}) == 2
            assert await db.document_bindings.find_one({"file_id": file_id})
        finally:
            await db.steps.delete_one({"_id": step_id})
            await db.step_versions.delete_many({"step_id": str(step_id)})
            await db.user_progress.delete_many({"user_id": user_id})
            await db.user_progress_revisions.delete_many({"user_id": user_id})
            await db.document_bindings.delete_many({"user_id": user_id})
            await db.files.delete_many({"id": file_id})
            client.close()

    asyncio.run(scenario())


def test_existing_records_are_migrated_idempotently():
    async def scenario():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        db = client[os.environ["DB_NAME"]]
        token = str(ObjectId())
        step_id = ObjectId()
        try:
            await db.steps.insert_one({
                "_id": step_id, "survey_id": token, "title": "Legacy", "description": "",
                "order": 7, "step_type": "form", "is_active": True,
            })
            await db.user_progress.insert_one({
                "user_id": token, "step_id": str(step_id), "survey_id": token,
                "step_order": 7, "status": "completed", "data": {"legacy": True},
            })
            await migrate_step_answer_versioning(db)
            await migrate_step_answer_versioning(db)
            assert await db.step_versions.count_documents({"step_id": str(step_id)}) == 1
            assert await db.user_progress_revisions.count_documents({"user_id": token}) == 1
            current = await db.user_progress.find_one({"user_id": token})
            assert current["step_version"] == 1 and current["revision"] == 1
        finally:
            await db.steps.delete_one({"_id": step_id})
            await db.step_versions.delete_many({"step_id": str(step_id)})
            await db.user_progress.delete_many({"user_id": token})
            await db.user_progress_revisions.delete_many({"user_id": token})
            client.close()

    asyncio.run(scenario())
