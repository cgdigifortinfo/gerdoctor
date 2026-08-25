"""User dashboard read models for the active survey runtime."""
from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from typing import Any, Protocol, cast

from slices.document_workflow.mappers import document_workflow_context
from slices.document_workflow.service import DocumentWorkflowService


class SurveyDashboardRepository(Protocol):
    async def steps(self, survey_id: str) -> list[dict[str, Any]]: ...
    async def progress(self, user_id: str, survey_id: str) -> list[dict[str, Any]]: ...
    async def history(self, user_id: str) -> list[dict[str, Any]]: ...
    async def bootstrap(
        self, user_id: str, survey_id: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]: ...


class MongoSurveyDashboardRepository:
    def __init__(self, database: Any) -> None:
        self._database = database

    @staticmethod
    def _step_query(survey_id: str) -> dict[str, Any]:
        return {"survey_id": survey_id, "is_active": True, "is_deleted": {"$ne": True}}

    async def steps(self, survey_id: str) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], await self._database.steps.find(
            self._step_query(survey_id),
        ).sort("order", 1).to_list(100))

    async def progress(self, user_id: str, survey_id: str) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], await self._database.user_progress.find({
            "user_id": user_id, "survey_id": survey_id,
        }, {"_id": 0}).to_list(100))

    async def history(self, user_id: str) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], await self._database.progress_history.find({
            "user_id": user_id,
        }, {"_id": 0}).sort("timestamp", -1).to_list(200))

    async def bootstrap(
        self, user_id: str, survey_id: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
        steps, progress, history, settings = await asyncio.gather(
            self.steps(survey_id), self.progress(user_id, survey_id), self.history(user_id),
            self._database.site_settings.find_one({"_key": "global"}, {"_id": 0, "_key": 0}),
        )
        return steps, progress, history, cast(dict[str, Any], settings or {})


Metrics = Callable[[list[dict[str, Any]], list[dict[str, Any]]], dict[str, Any]]


def serialized_step(step: Mapping[str, Any]) -> dict[str, Any]:
    return {**{key: value for key, value in step.items() if key != "_id"}, "id": str(step["_id"])}


def all_step_data(
    steps: list[dict[str, Any]], progress: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    progress_by_step = {str(row["step_id"]): row for row in progress}
    return [{
        "step_id": str(step["_id"]), "order": step["order"], "title": step["title"],
        "step_type": step["step_type"],
        "status": progress_by_step.get(str(step["_id"]), {}).get("status", "pending"),
        "data": progress_by_step.get(str(step["_id"]), {}).get("data", {}),
        "conditions": step.get("conditions", []),
        "field_mappings": step.get("field_mappings", []),
        "required_fields": step.get("required_fields", []),
        "required_uploads": step.get("required_uploads", []),
    } for step in steps]


class SurveyDashboardService:
    def __init__(self, repository: SurveyDashboardRepository, metrics: Metrics) -> None:
        self._repository = repository
        self._metrics = metrics

    async def steps(self, survey_id: str) -> list[dict[str, Any]]:
        return [serialized_step(step) for step in await self._repository.steps(survey_id)]

    async def progress(self, user_id: str, survey_id: str) -> list[dict[str, Any]]:
        return await self._repository.progress(user_id, survey_id)

    async def all_data(self, user_id: str, survey_id: str) -> list[dict[str, Any]]:
        steps, progress = await asyncio.gather(
            self._repository.steps(survey_id), self._repository.progress(user_id, survey_id),
        )
        return all_step_data(steps, progress)

    async def bootstrap(
        self, user: Mapping[str, Any], survey_id: str,
    ) -> dict[str, Any]:
        user_id = str(user["_id"])
        steps, progress, history, settings = await self._repository.bootstrap(user_id, survey_id)
        active_ids = {str(step["_id"]) for step in steps}
        live_progress = [row for row in progress if row.get("step_id") in active_ids]
        metrics = self._metrics(steps, live_progress)
        workflow = DocumentWorkflowService.resolve(document_workflow_context(steps, live_progress))
        serialized = [serialized_step(step) for step in steps]
        serialized = [
            {**step, **workflow[step["id"]].as_dict()} if step["id"] in workflow else step
            for step in serialized
        ]
        return {
            "steps": serialized,
            "progress": live_progress,
            "all_step_data": all_step_data(steps, live_progress),
            "notification_preferences": user.get("notification_preferences", {
                "email_on_step_enter": True,
                "email_on_step_edit": False,
                "email_on_step_leave": True,
            }),
            "history": history,
            "estimated_completion": metrics.get("estimated_completion"),
            "settings": settings,
        }

    async def history(self, user_id: str) -> list[dict[str, Any]]:
        return await self._repository.history(user_id)
