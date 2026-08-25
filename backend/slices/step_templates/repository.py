"""MongoDB adapter for step templates."""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any, cast
from infrastructure.mongo_ids import object_id_or_none


class MongoStepTemplateRepository:
    def __init__(self, database: Any) -> None: self._db = database
    async def templates(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], await self._db.step_templates.find().sort("created_at", -1).to_list(200))
    async def template(self, template_id: str) -> dict[str, Any] | None:
        oid = object_id_or_none(template_id)
        return cast(dict[str, Any] | None, await self._db.step_templates.find_one({"_id": oid})) if oid else None
    async def insert_template(self, document: Mapping[str, Any]) -> str:
        return str((await self._db.step_templates.insert_one(dict(document))).inserted_id)
    async def update_template(self, template_id: str, fields: Mapping[str, Any]) -> None:
        oid = object_id_or_none(template_id)
        if oid: await self._db.step_templates.update_one({"_id": oid}, {"$set": dict(fields)})
    async def delete_template(self, template_id: str) -> None:
        oid = object_id_or_none(template_id)
        if oid: await self._db.step_templates.delete_one({"_id": oid})
    async def step(self, step_id: str) -> dict[str, Any] | None:
        oid = object_id_or_none(step_id)
        return cast(dict[str, Any] | None, await self._db.steps.find_one({"_id": oid})) if oid else None
    async def shifted_steps(self, survey_id: str, order: int) -> list[dict[str, Any]]:
        cursor = self._db.steps.find({"survey_id": survey_id, "order": {"$gte": order},
                                      "is_deleted": {"$ne": True}}).sort("order", -1)
        return cast(list[dict[str, Any]], await cursor.to_list(1000))
    async def insert_step(self, document: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
        result = await self._db.steps.insert_one(dict(document))
        step = cast(dict[str, Any], await self._db.steps.find_one({"_id": result.inserted_id}))
        return str(result.inserted_id), step
    async def survey_user_ids(self, survey_id: str) -> list[str]:
        # Applying a template is a global survey migration. Silently truncating
        # this set would leave older users without the new pending revision.
        rows = await self._db.users.find(
            {"role": "user", "survey_id": survey_id}, {"_id": 1},
        ).to_list(None)
        return [str(row["_id"]) for row in rows]
