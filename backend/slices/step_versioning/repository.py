"""Mongo persistence for immutable step versions and answer revisions."""
from __future__ import annotations

from typing import Any, Mapping, Sequence, cast

from slices.step_versioning.models import MigrationStats
from slices.step_versioning.domain import answer_history_item, document_binding, file_references, progress_revision_plan, step_version_document
from infrastructure.clock import Clock
from infrastructure.mongo_ids import object_id_or_none, valid_object_ids
from infrastructure.mongo_serialization import mongo_json_safe


class MongoStepVersioningRepository:
    def __init__(self, database: Any, clock: Clock) -> None:
        self._db, self._clock = database, clock

    async def insert_step_version(self, step: Mapping[str, Any], version: int, actor: Mapping[str, Any] | None, change_type: str) -> dict[str, Any]:
        document = step_version_document(str(step["_id"]), mongo_json_safe(dict(step)), version, mongo_json_safe(dict(actor or {})), change_type, self._clock.now_iso())
        await self._db.step_versions.update_one({"step_id": document["step_id"], "version": version}, {"$setOnInsert": document}, upsert=True)
        return document

    async def ensure_step_version(self, step: Mapping[str, Any], actor: Mapping[str, Any] | None = None, change_type: str = "migration") -> int:
        mutable_step = dict(step)
        object_id = object_id_or_none(mutable_step.get("id"))
        if "_id" not in mutable_step and object_id is not None:
            stored = await self._db.steps.find_one({"_id": object_id})
            if not stored:
                raise ValueError("Step does not exist")
            mutable_step = stored
        version = int(mutable_step.get("current_version") or 1)
        if not mutable_step.get("current_version"):
            deleted = bool(mutable_step.get("is_deleted", False))
            await self._db.steps.update_one({"_id": mutable_step["_id"]}, {"$set": {"current_version": version, "is_deleted": deleted}})
            mutable_step = {**mutable_step, "current_version": version, "is_deleted": deleted}
        await self.insert_step_version(mutable_step, version, actor, change_type)
        return version

    async def update_step_versioned(self, step: Mapping[str, Any], set_fields: Mapping[str, Any], unset_fields: Sequence[str] | None, actor: Mapping[str, Any], change_type: str) -> tuple[int, int, dict[str, Any]]:
        before, now = await self.ensure_step_version(step), self._clock.now_iso()
        after = before + 1
        operation: dict[str, Any] = {"$set": {**set_fields, "current_version": after, "updated_at": now}}
        if unset_fields:
            operation["$unset"] = {field: "" for field in unset_fields}
        await self._db.steps.update_one({"_id": step["_id"]}, operation)
        updated = await self._db.steps.find_one({"_id": step["_id"]})
        await self.insert_step_version(updated, after, actor, change_type)
        return before, after, updated

    async def bind_revision_documents(self, revision: Mapping[str, Any]) -> int:
        count = 0
        for path, entry in file_references(revision.get("data") or {}):
            binding = document_binding(revision, path, entry)
            keys = ("file_id", "user_id", "step_id", "step_version", "progress_revision", "field_path")
            await self._db.document_bindings.update_one({key: binding[key] for key in keys}, {"$setOnInsert": binding}, upsert=True)
            await self._db.files.update_one({"id": binding["file_id"]}, {"$set": {"historical_protected": True}, "$addToSet": {"bound_step_ids": revision["step_id"]}})
            count += 1
        return count

    async def write_progress_revision(self, *, user_id: str, step: Mapping[str, Any], status: str, data: Mapping[str, Any] | None, actor: Mapping[str, Any] | None, change_type: str, extra_fields: Mapping[str, Any] | None = None, unset_fields: Sequence[str] | None = None) -> dict[str, Any]:
        step_id = str(step.get("_id") or step.get("id"))
        existing = await self._db.user_progress.find_one({"user_id": user_id, "step_id": step_id})
        step_version = await self.ensure_step_version(step)
        revision_number = int((existing or {}).get("revision") or 0) + 1
        plan = progress_revision_plan(existing=existing, step=step, user_id=user_id, status=status, data=data, step_version=step_version, revision=revision_number, actor=mongo_json_safe(dict(actor or {})), change_type=change_type, changed_at=self._clock.now_iso(), extra_fields=extra_fields, unset_fields=unset_fields)
        operation: dict[str, Any] = {"$set": dict(plan.current)}
        if plan.unset_fields:
            operation["$unset"] = {field: "" for field in plan.unset_fields}
        await self._db.user_progress.update_one({"user_id": user_id, "step_id": step_id}, operation, upsert=True)
        revision_document = cast(dict[str, Any], mongo_json_safe(dict(plan.revision)))
        await self._db.user_progress_revisions.update_one({"user_id": user_id, "step_id": step_id, "revision": revision_number}, {"$setOnInsert": revision_document}, upsert=True)
        await self.bind_revision_documents(revision_document)
        return revision_document

    async def migrate(self) -> dict[str, int]:
        stats = MigrationStats()
        async for step in self._db.steps.find({"current_version": {"$exists": False}}):
            await self.ensure_step_version(step)
            stats = MigrationStats(stats.steps + 1, stats.answers, stats.documents)
        async for progress in self._db.user_progress.find({"$or": [{"revision": {"$exists": False}}, {"step_version": {"$exists": False}}]}):
            step_id, object_id = progress.get("step_id"), object_id_or_none(progress.get("step_id"))
            step = await self._db.steps.find_one({"_id": object_id}) if object_id is not None else None
            step_version = int(progress.get("step_version") or (step or {}).get("current_version") or 1)
            revision_number = int(progress.get("revision") or 1)
            await self._db.user_progress.update_one({"_id": progress["_id"]}, {"$set": {"step_version": step_version, "revision": revision_number}})
            revision = {**mongo_json_safe(progress), "step_version": step_version, "revision": revision_number, "created_at": progress.get("updated_at") or progress.get("completed_at") or self._clock.now_iso(), "change_type": "migration", "changed_by": {"role": "system"}}
            await self._db.user_progress_revisions.update_one({"user_id": progress["user_id"], "step_id": step_id, "revision": revision_number}, {"$setOnInsert": revision}, upsert=True)
            bound = await self.bind_revision_documents(revision)
            stats = MigrationStats(stats.steps, stats.answers + 1, stats.documents + bound)
        return stats.as_dict()

    async def revision_view(self, user_id: str) -> list[dict[str, Any]]:
        rows = await self._db.user_progress_revisions.find({"user_id": user_id}, {"_id": 0}).sort([("step_order", 1), ("revision", -1)]).to_list(5000)
        step_ids = list({row.get("step_id") for row in rows if row.get("step_id")})
        steps = await self._db.steps.find({"_id": {"$in": list(valid_object_ids(step_ids))}}).to_list(1000)
        current = {str(step["_id"]): mongo_json_safe(step) for step in steps}
        versions = await self._db.step_versions.find({"step_id": {"$in": step_ids}}, {"_id": 0}).to_list(10000)
        snapshots = {(row["step_id"], row["version"]): row for row in versions}
        return [answer_history_item(row, current.get(row.get("step_id")), snapshots.get((row.get("step_id"), row.get("step_version")))) for row in rows]
