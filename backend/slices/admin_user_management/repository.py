"""MongoDB adapter for administrative user management."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from typing import Any, cast
from infrastructure.mongo_ids import object_id_or_none


class MongoAdminUserRepository:
    def __init__(self, database: Any) -> None: self._db = database
    async def search(self, query: Mapping[str, Any]) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], await self._db.users.find(dict(query), {"password_hash": 0}).to_list(1000))
    async def user(self, user_id: str) -> dict[str, Any] | None:
        oid = object_id_or_none(user_id)
        return cast(dict[str, Any] | None, await self._db.users.find_one({"_id": oid})) if oid else None
    async def user_by_email(self, email: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, await self._db.users.find_one({"email": email}))
    async def partner(self, partner_id: str) -> dict[str, Any] | None:
        oid = object_id_or_none(partner_id)
        return cast(dict[str, Any] | None, await self._db.partners.find_one({"_id": oid})) if oid else None
    async def survey(self, survey_id: str) -> dict[str, Any] | None:
        oid = object_id_or_none(survey_id)
        return cast(dict[str, Any] | None, await self._db.surveys.find_one({"_id": oid, "is_active": True})) if oid else None
    async def insert_user(self, document: Mapping[str, Any]) -> str:
        result = await self._db.users.insert_one(dict(document)); return str(result.inserted_id)
    async def survey_steps(self, survey_id: str) -> list[dict[str, Any]]:
        oid = object_id_or_none(survey_id)
        query = {"$or": [{"survey_id": survey_id}, {"survey_id": oid}], "is_deleted": {"$ne": True}}
        return cast(list[dict[str, Any]], await self._db.steps.find(query).sort("order", 1).to_list(100))
    async def insert_progress(self, documents: Sequence[Mapping[str, Any]]) -> None:
        if documents: await self._db.user_progress.insert_many([dict(item) for item in documents])
    async def link_partner(self, partner_id: str, user_id: str) -> None:
        oid = object_id_or_none(partner_id)
        if oid: await self._db.partners.update_one({"_id": oid}, {"$set": {"user_id": user_id}})
    async def update_user(self, user_id: str, fields: Mapping[str, Any]) -> bool:
        oid = object_id_or_none(user_id)
        if not oid: return False
        result = await self._db.users.update_one({"_id": oid}, {"$set": dict(fields)})
        return bool(result.modified_count)
    async def unlink_partners(self, user_id: str, partner_id: str | None) -> None:
        oid = object_id_or_none(partner_id) if partner_id else None
        if oid: await self._db.partners.update_one({"_id": oid}, {"$unset": {"user_id": ""}})
        await self._db.partners.update_many({"linked_user_ids": user_id}, {"$pull": {"linked_user_ids": user_id}})
