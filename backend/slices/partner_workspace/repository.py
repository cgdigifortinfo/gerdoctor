"""MongoDB adapter for partner user workspace data."""
from __future__ import annotations

from typing import Any

from infrastructure.mongo_ids import object_id_or_none

from slices.partner_workspace.mappers import (
    workspace_progress_from_document,
    workspace_step_from_document,
    workspace_user_from_document,
)
from slices.partner_workspace.models import WorkspaceProgress, WorkspaceStep, WorkspaceUser


class MongoPartnerWorkspaceRepository:
    def __init__(self, database: Any) -> None:
        self._db = database

    async def find_user(self, user_id: str) -> WorkspaceUser | None:
        object_id = object_id_or_none(user_id)
        if object_id is None:
            return None
        document = await self._db.users.find_one({"_id": object_id}, {"password_hash": 0})
        return workspace_user_from_document(document) if document else None

    async def load_progress(self, user_id: str, survey_id: str | None) -> tuple[WorkspaceProgress, ...]:
        query: dict[str, Any] = {"user_id": user_id}
        if survey_id:
            query["survey_id"] = survey_id
        documents = await self._db.user_progress.find(query, {"_id": 0}).to_list(500)
        return tuple(workspace_progress_from_document(document) for document in documents)

    async def load_steps(self, survey_id: str | None) -> tuple[WorkspaceStep, ...]:
        query: dict[str, Any] = {"is_active": True, "is_deleted": {"$ne": True}}
        if survey_id:
            query["survey_id"] = survey_id
        documents = await self._db.steps.find(query).sort("order", 1).to_list(500)
        return tuple(workspace_step_from_document(document) for document in documents)
