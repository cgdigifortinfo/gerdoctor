"""Mongo read adapter for partner-owned user workspaces."""
from __future__ import annotations

from typing import Any, cast

from infrastructure.mongo_ids import object_id_or_none, valid_object_ids


class MongoPartnerWorkspaceReadRepository:
    def __init__(self, database: Any) -> None: self._db = database

    async def partner(self, partner_id: str) -> dict[str, Any] | None:
        object_id = object_id_or_none(partner_id)
        return cast(dict[str, Any] | None, await self._db.partners.find_one(
            {"_id": object_id},
        )) if object_id else None

    async def submissions(self, partner_id: str) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], await self._db.partner_submissions.find(
            {"partner_id": partner_id}, {"_id": 0},
        ).to_list(None))

    async def step_one_data(self, user_ids: set[str]) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        if not user_ids: return result
        async for row in self._db.user_progress.find(
            {"user_id": {"$in": list(user_ids)}, "step_order": 1},
            {"user_id": 1, "data": 1},
        ):
            result[str(row["user_id"])] = dict(row.get("data") or {})
        return result

    async def users(self, user_ids: set[str] | None = None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"role": "user"}
        if user_ids is not None:
            query["_id"] = {"$in": valid_object_ids(user_ids)}
        return cast(list[dict[str, Any]], await self._db.users.find(
            query, {"password_hash": 0},
        ).to_list(None))

    async def submitted_user_ids(self, partner_id: str) -> set[str]:
        rows = await self._db.partner_submissions.find(
            {"partner_id": partner_id}, {"user_id": 1},
        ).to_list(None)
        return {str(row["user_id"]) for row in rows if row.get("user_id")}
