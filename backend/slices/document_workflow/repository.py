"""Mongo adapter for document-workflow runtime reads."""
from __future__ import annotations

from typing import Any

from slices.document_workflow.mappers import document_workflow_context
from slices.document_workflow.models import DocumentWorkflowContext


class MongoDocumentWorkflowRepository:
    def __init__(self, database: Any) -> None:
        self._db = database

    async def load(self, user_id: str, survey_id: str | None) -> DocumentWorkflowContext:
        step_query: dict[str, Any] = {"is_active": True, "is_deleted": {"$ne": True}}
        progress_query: dict[str, Any] = {"user_id": user_id}
        if survey_id:
            step_query["survey_id"] = survey_id
            progress_query["survey_id"] = survey_id
        steps = await self._db.steps.find(step_query).sort("order", 1).to_list(200)
        progress = await self._db.user_progress.find(progress_query, {"_id": 0}).to_list(500)
        return document_workflow_context(steps, progress)
