"""Mongo adapter for survey progress commands."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from infrastructure.mongo_ids import object_id_or_none


class MongoSurveyProgressRepository:
    def __init__(self, database: Any) -> None: self._db = database

    async def step(self, step_id: str) -> dict[str, Any] | None:
        object_id = object_id_or_none(step_id)
        if object_id is None: return None
        return cast(dict[str, Any] | None, await self._db.steps.find_one({"_id": object_id}))

    async def progress(self, user_id: str, step_id: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, await self._db.user_progress.find_one(
            {"user_id": user_id, "step_id": step_id},
        ))

    async def step_count(self, survey_id: str) -> int:
        return int(await self._db.steps.count_documents({
            "survey_id": survey_id, "is_deleted": {"$ne": True}, "is_active": True,
        }))

    async def history(self, document: Mapping[str, Any]) -> None:
        await self._db.progress_history.insert_one(dict(document))
