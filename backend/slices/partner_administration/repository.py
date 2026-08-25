"""Mongo adapter for partner administration."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from infrastructure.mongo_ids import object_id_or_none, valid_object_ids


class MongoPartnerAdministrationRepository:
    def __init__(self, database: Any) -> None:
        self._db = database

    async def insert(self, document: Mapping[str, Any]) -> str:
        result = await self._db.partners.insert_one(dict(document))
        return str(result.inserted_id)

    async def find(self, partner_id: str) -> dict[str, Any] | None:
        object_id = object_id_or_none(partner_id)
        return cast(dict[str, Any] | None, await self._db.partners.find_one({"_id": object_id})) if object_id is not None else None

    async def update(self, partner_id: str, fields: Mapping[str, Any]) -> dict[str, Any] | None:
        object_id = object_id_or_none(partner_id)
        if object_id is None:
            return None
        await self._db.partners.update_one({"_id": object_id}, {"$set": dict(fields)})
        return cast(dict[str, Any] | None, await self._db.partners.find_one({"_id": object_id}))

    async def valid_survey_count(self, survey_ids: Sequence[str]) -> int:
        return int(await self._db.surveys.count_documents({"_id": {"$in": list(valid_object_ids(survey_ids))}}))

    async def valid_priced_step_count(self, step_ids: Sequence[str]) -> int:
        if not step_ids:
            return 0
        return int(await self._db.steps.count_documents({
            "_id": {"$in": list(valid_object_ids(step_ids))},
            "step_type": {"$in": ["partner_selection", "partner_multiselection"]},
        }))

    async def find_user(self, user_id: str) -> dict[str, Any] | None:
        object_id = object_id_or_none(user_id)
        return await self._db.users.find_one({"_id": object_id}) if object_id is not None else None

    async def users_for_partner(self, partner_id: str) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], await self._db.users.find({"partner_id": partner_id}).to_list(100))

    async def set_user_role(self, user_id: str, fields: Mapping[str, Any], remove_partner: bool) -> None:
        object_id = object_id_or_none(user_id)
        if object_id is None:
            return
        operation: dict[str, Any] = {"$set": dict(fields)}
        if remove_partner:
            operation["$unset"] = {"partner_id": ""}
        await self._db.users.update_one({"_id": object_id}, operation)

    async def set_primary_user(self, partner_id: str, user_id: str | None) -> None:
        object_id = object_id_or_none(partner_id)
        if object_id is None:
            return
        operation = {"$set": {"user_id": user_id}} if user_id is not None else {"$unset": {"user_id": ""}}
        await self._db.partners.update_one({"_id": object_id}, operation)

    async def delete(self, partner_id: str) -> None:
        object_id = object_id_or_none(partner_id)
        if object_id is None:
            return
        await self._db.partner_submissions.delete_many({"partner_id": partner_id})
        await self._db.partners.delete_one({"_id": object_id})
