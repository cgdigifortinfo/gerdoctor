"""MongoDB adapter for survey runtime reads."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from slices.survey_runtime.mappers import runtime_context_from_documents
from slices.survey_runtime.models import SurveyRuntimeContext
from infrastructure.mongo_ids import object_id_or_none, valid_object_ids


class MongoSurveyRuntimeRepository:
    def __init__(self, database: Any) -> None:
        self._db = database

    async def load(self, user_id: str) -> SurveyRuntimeContext:
        object_id = object_id_or_none(user_id)
        user = await self._db.users.find_one({"_id": object_id}) if object_id is not None else None
        survey_id = user.get("survey_id") if user else None
        step_query: dict[str, Any] = {"is_active": True, "is_deleted": {"$ne": True}}
        progress_query: dict[str, Any] = {"user_id": user_id}
        if survey_id:
            step_query["survey_id"] = survey_id
            progress_query["survey_id"] = survey_id
        steps = await self._db.steps.find(step_query).sort("order", 1).to_list(200)
        progress = await self._db.user_progress.find(progress_query, {"_id": 0}).to_list(500)
        return runtime_context_from_documents(steps, progress)

    async def load_many(self, user_ids: tuple[str, ...]) -> dict[str, SurveyRuntimeContext]:
        unique_ids = tuple(dict.fromkeys(user_id for user_id in user_ids if user_id))
        if not unique_ids:
            return {}
        object_ids = valid_object_ids(unique_ids)
        users = await self._db.users.find(
            {"_id": {"$in": object_ids}}, {"survey_id": 1}
        ).to_list(len(object_ids) or 1)
        survey_by_user = {str(user["_id"]): user.get("survey_id") for user in users}
        survey_ids = {survey_id for survey_id in survey_by_user.values() if survey_id}
        step_query: dict[str, Any] = {"is_active": True, "is_deleted": {"$ne": True}}
        if survey_ids:
            step_query["survey_id"] = {"$in": list(survey_ids)}
        steps = await self._db.steps.find(step_query).sort([("survey_id", 1), ("order", 1)]).to_list(1000)
        steps_by_survey: dict[Any, list[dict[str, Any]]] = defaultdict(list)
        for step in steps:
            steps_by_survey[step.get("survey_id")].append(step)
        rows = await self._db.user_progress.find(
            {"user_id": {"$in": list(unique_ids)}}, {"_id": 0}
        ).to_list(max(1000, len(unique_ids) * 100))
        progress_by_user: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            progress_by_user[str(row.get("user_id", ""))].append(row)
        return {
            user_id: runtime_context_from_documents(
                steps_by_survey.get(survey_by_user.get(user_id), []),
                progress_by_user.get(user_id, []),
            )
            for user_id in unique_ids
        }
