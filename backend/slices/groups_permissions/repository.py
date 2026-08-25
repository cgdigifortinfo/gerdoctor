"""MongoDB adapter for permission-group administration."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from infrastructure.mongo_ids import object_id_or_none, valid_object_ids


class MongoGroupsPermissionsRepository:
    def __init__(self, database: Any) -> None:
        self._db = database

    async def list_groups(self) -> list[dict[str, Any]]:
        cursor = self._db.permission_groups.find({}).sort([("role", 1), ("name", 1)])
        return cast(list[dict[str, Any]], await cursor.to_list(500))

    async def find_group(self, group_id: str) -> dict[str, Any] | None:
        object_id = object_id_or_none(group_id)
        if object_id is None:
            return None
        return cast(dict[str, Any] | None, await self._db.permission_groups.find_one({"_id": object_id}))

    async def find_group_by_name(self, name_key: str, excluding_id: str | None = None) -> dict[str, Any] | None:
        query: dict[str, Any] = {"name_key": name_key}
        excluded = object_id_or_none(excluding_id) if excluding_id else None
        if excluded is not None:
            query["_id"] = {"$ne": excluded}
        return cast(dict[str, Any] | None, await self._db.permission_groups.find_one(query))

    async def member_count(self, group_id: str) -> int:
        return int(await self._db.users.count_documents({
            "group_ids": group_id, "is_deleted": {"$ne": True},
        }))

    async def insert_group(self, document: Mapping[str, Any]) -> dict[str, Any]:
        saved = dict(document)
        result = await self._db.permission_groups.insert_one(saved)
        saved["_id"] = result.inserted_id
        return saved

    async def update_group(self, group_id: str, fields: Mapping[str, object]) -> dict[str, Any] | None:
        object_id = object_id_or_none(group_id)
        if object_id is None:
            return None
        await self._db.permission_groups.update_one({"_id": object_id}, {"$set": dict(fields)})
        return cast(dict[str, Any] | None, await self._db.permission_groups.find_one({"_id": object_id}))

    async def delete_group(self, group_id: str) -> None:
        object_id = object_id_or_none(group_id)
        if object_id is not None:
            await self._db.permission_groups.delete_one({"_id": object_id})

    async def compatible_group_ids(self, group_ids: Sequence[str], role: str) -> list[str]:
        object_ids = list(valid_object_ids(group_ids))
        if not object_ids:
            return []
        cursor = self._db.permission_groups.find({"_id": {"$in": object_ids}, "role": role}, {"_id": 1})
        return [str(group["_id"]) async for group in cursor]
