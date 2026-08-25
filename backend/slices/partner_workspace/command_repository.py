"""Mongo command adapter for partner-owned user progress."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from infrastructure.mongo_ids import object_id_or_none


class MongoPartnerWorkspaceCommandRepository:
    def __init__(self, database: Any) -> None: self._db = database

    async def partner(self, partner_id: str) -> dict[str, Any] | None:
        object_id = object_id_or_none(partner_id)
        return cast(dict[str, Any] | None, await self._db.partners.find_one(
            {"_id": object_id},
        )) if object_id else None

    async def step(self, step_id: str) -> dict[str, Any] | None:
        object_id = object_id_or_none(step_id)
        return cast(dict[str, Any] | None, await self._db.steps.find_one(
            {"_id": object_id},
        )) if object_id else None

    async def user(self, user_id: str) -> dict[str, Any] | None:
        object_id = object_id_or_none(user_id)
        return cast(dict[str, Any] | None, await self._db.users.find_one(
            {"_id": object_id}, {"password_hash": 0},
        )) if object_id else None

    async def progress(self, user_id: str, step_id: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, await self._db.user_progress.find_one(
            {"user_id": user_id, "step_id": step_id},
        ))

    async def update_progress(self, user_id: str, step_id: str,
                              update: Mapping[str, Any], *, upsert: bool = True) -> None:
        await self._db.user_progress.update_one(
            {"user_id": user_id, "step_id": step_id}, dict(update), upsert=upsert,
        )

    async def history(self, document: Mapping[str, Any], *, tolerant: bool = False) -> None:
        try: await self._db.progress_history.insert_one(dict(document))
        except Exception:
            if not tolerant: raise

    async def active_step_count(self) -> int:
        return int(await self._db.steps.count_documents({"is_active": True}))
