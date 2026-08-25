"""Mongo/versioning adapter for Step Configuration commands."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Mapping, cast

from infrastructure.mongo_ids import object_id_or_none
class MongoStepConfigurationRepository:
    def __init__(
        self, database: Any,
        insert_version: Callable[..., Awaitable[Any]],
        update_versioned: Callable[..., Awaitable[tuple[int, int, Mapping[str, Any]]]],
    ) -> None:
        self._db = database
        self._insert_version = insert_version
        self._update_versioned = update_versioned

    async def create(self, values: Mapping[str, Any], actor: Mapping[str, Any]) -> str:
        result = await self._db.steps.insert_one(dict(values))
        created = await self._db.steps.find_one({"_id": result.inserted_id})
        await self._insert_version(self._db, created, 1, dict(actor), "create")
        return str(result.inserted_id)

    async def find(self, step_id: str, include_deleted: bool = False) -> Mapping[str, Any] | None:
        object_id = object_id_or_none(step_id)
        if object_id is None:
            return None
        query: dict[str, Any] = {"_id": object_id}
        if not include_deleted:
            query["is_deleted"] = {"$ne": True}
        return cast(Mapping[str, Any] | None, await self._db.steps.find_one(query))

    async def update(
        self, step_id: str, values: Mapping[str, Any], unset_fields: tuple[str, ...],
        actor: Mapping[str, Any], change_type: str,
    ) -> tuple[int, int]:
        step = await self.find(step_id)
        if step is None:
            raise KeyError(step_id)
        before, after, _ = await self._update_versioned(
            self._db, dict(step), dict(values), list(unset_fields), dict(actor), change_type,
        )
        return before, after
