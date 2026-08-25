"""Mongo identity lookup adapter."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from infrastructure.mongo_ids import object_id_or_none


class InvalidUserIdentifier(ValueError):
    pass


class MongoIdentityRepository:
    def __init__(self, database: Any) -> None:
        self._db = database

    async def find_user(self, user_id: object) -> dict[str, Any] | None:
        object_id = object_id_or_none(user_id)
        if object_id is None:
            raise InvalidUserIdentifier
        return cast(dict[str, Any] | None, await self._db.users.find_one({"_id": object_id}))
    async def user_by_email(self, email: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, await self._db.users.find_one({"email": email}))
    async def insert_user(self, document: Mapping[str, Any]) -> tuple[str, object]:
        result = await self._db.users.insert_one(dict(document)); return str(result.inserted_id), result.inserted_id
    async def update_user(self, user_id: object, fields: Mapping[str, Any]) -> None:
        object_id = object_id_or_none(user_id)
        if object_id: await self._db.users.update_one({"_id": object_id}, {"$set": dict(fields)})
    async def steps(self, survey_id: str) -> list[dict[str, Any]]:
        query = {"survey_id": survey_id, "is_deleted": {"$ne": True}, "is_active": True}
        return cast(list[dict[str, Any]], await self._db.steps.find(query).sort("order", 1).to_list(100))
    async def insert_progress(self, documents: Sequence[Mapping[str, Any]]) -> None:
        if documents: await self._db.user_progress.insert_many([dict(item) for item in documents])
    async def insert_partner(self, document: Mapping[str, Any]) -> str:
        return str((await self._db.partners.insert_one(dict(document))).inserted_id)
    async def login_attempt(self, identifier: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, await self._db.login_attempts.find_one({"identifier": identifier}))
    async def record_failed_login(self, identifier: str, lockout_until: str) -> None:
        await self._db.login_attempts.update_one({"identifier": identifier},
            {"$inc": {"count": 1}, "$set": {"lockout_until": lockout_until}}, upsert=True)
    async def clear_login_attempt(self, identifier: str) -> None:
        await self._db.login_attempts.delete_one({"identifier": identifier})
    async def consume_reset_tokens(self, user_id: str) -> None:
        await self._db.password_reset_tokens.update_many({"user_id": user_id, "used": False}, {"$set": {"used": True}})
    async def insert_reset_token(self, document: Mapping[str, Any]) -> None:
        await self._db.password_reset_tokens.insert_one(dict(document))
    async def reset_token(self, token: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, await self._db.password_reset_tokens.find_one({"token": token, "used": False}))
    async def mark_reset_token_used(self, token: str) -> None:
        await self._db.password_reset_tokens.update_one({"token": token}, {"$set": {"used": True}})
