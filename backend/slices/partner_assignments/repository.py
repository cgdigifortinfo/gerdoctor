"""MongoDB adapter for partner assignment contexts."""
from __future__ import annotations

from typing import Any

from infrastructure.mongo_ids import valid_object_ids

from slices.partner_assignments.mappers import flow_step_from_document, progress_from_document
from slices.partner_assignments.models import AssignmentContext, FlowStep, StepProgress


class MongoPartnerAssignmentRepository:
    def __init__(self, database: Any) -> None:
        self._db = database

    async def load_context(self, user_ids: tuple[str, ...]) -> AssignmentContext:
        object_ids = valid_object_ids(user_ids)
        users = await self._db.users.find(
            {"_id": {"$in": object_ids}}, {"survey_id": 1},
        ).to_list(len(object_ids) or 1)
        survey_by_user: dict[str, str | None] = {
            str(user["_id"]): user.get("survey_id") for user in users
        }
        survey_ids = tuple({survey_id for survey_id in survey_by_user.values() if survey_id})
        step_documents = await self._db.steps.find(
            {
                "is_active": True,
                "is_deleted": {"$ne": True},
                "survey_id": {"$in": list(survey_ids)},
            },
            {"_id": 1, "survey_id": 1, "order": 1, "step_type": 1},
        ).sort([("survey_id", 1), ("order", 1)]).to_list(1000)
        steps_by_survey: dict[str, list[FlowStep]] = {}
        for document in step_documents:
            steps_by_survey.setdefault(document.get("survey_id"), []).append(
                flow_step_from_document(document),
            )
        progress_documents = await self._db.user_progress.find(
            {"user_id": {"$in": list(user_ids)}}, {"_id": 0},
        ).to_list(max(1000, len(user_ids) * 100))
        progress_by_user: dict[str, list[StepProgress]] = {}
        for document in progress_documents:
            progress_by_user.setdefault(document.get("user_id"), []).append(
                progress_from_document(document),
            )
        return AssignmentContext(
            steps_by_user={
                user_id: tuple(steps_by_survey.get(survey_by_user.get(user_id) or "", ()))
                for user_id in user_ids
            },
            progress_by_user={
                user_id: tuple(progress_by_user.get(user_id, ())) for user_id in user_ids
            },
        )
