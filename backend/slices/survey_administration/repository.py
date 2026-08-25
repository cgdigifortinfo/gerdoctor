"""MongoDB survey repository."""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any, cast
from infrastructure.mongo_ids import object_id_or_none

class MongoSurveyAdministrationRepository:
    def __init__(self, database: Any) -> None: self._db = database
    async def surveys(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], await self._db.surveys.find().sort("name", 1).to_list(100))
    async def default_survey(self) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, await self._db.surveys.find_one({"is_default": True}))
    async def survey_by_slug(self, slug: str, active_only: bool = False) -> dict[str, Any] | None:
        query: dict[str, Any] = {"slug": slug}
        if active_only: query["is_active"] = True
        return cast(dict[str, Any] | None, await self._db.surveys.find_one(query))
    async def survey(self, survey_id: str) -> dict[str, Any] | None:
        oid = object_id_or_none(survey_id)
        return cast(dict[str, Any] | None, await self._db.surveys.find_one({"_id": oid})) if oid else None
    async def duplicate_slug(self, slug: str, excluding_id: str | None = None) -> bool:
        query: dict[str, Any] = {"slug": slug}
        oid = object_id_or_none(excluding_id) if excluding_id else None
        if oid: query["_id"] = {"$ne": oid}
        return bool(await self._db.surveys.find_one(query))
    async def clear_defaults(self, excluding_id: str | None = None) -> None:
        query: dict[str, Any] = {}
        oid = object_id_or_none(excluding_id) if excluding_id else None
        if oid: query["_id"] = {"$ne": oid}
        await self._db.surveys.update_many(query, {"$set": {"is_default": False}})
    async def insert(self, document: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
        result = await self._db.surveys.insert_one(dict(document))
        row = cast(dict[str, Any], await self._db.surveys.find_one({"_id": result.inserted_id}))
        return str(result.inserted_id), row
    async def update(self, survey_id: str, fields: Mapping[str, Any]) -> None:
        oid = object_id_or_none(survey_id)
        if oid: await self._db.surveys.update_one({"_id": oid}, {"$set": dict(fields)})
