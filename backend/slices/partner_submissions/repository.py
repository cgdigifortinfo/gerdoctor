"""MongoDB adapter for partner submission completion contexts."""
from __future__ import annotations

from typing import Any

from infrastructure.mongo_ids import valid_object_ids

from slices.partner_submissions.mappers import (
    submission_progress_from_document,
    submission_step_from_document,
)
from slices.partner_submissions.models import (
    SubmissionContext,
    SubmissionProgress,
    SubmissionStep,
)


class MongoPartnerSubmissionRepository:
    def __init__(self, database: Any) -> None:
        self._db = database

    async def load_context(self, user_ids: tuple[str, ...]) -> SubmissionContext:
        object_ids = valid_object_ids(user_ids)
        users = await self._db.users.find(
            {"_id": {"$in": object_ids}}, {"survey_id": 1},
        ).to_list(len(object_ids) or 1)
        survey_by_user = {
            str(user["_id"]): str(user.get("survey_id") or "") for user in users
        }
        survey_ids = tuple(dict.fromkeys(filter(None, survey_by_user.values())))

        step_documents = await self._db.steps.find(
            {
                "survey_id": {"$in": list(survey_ids)},
                "is_active": True,
                "is_deleted": {"$ne": True},
            },
            {"_id": 1, "survey_id": 1, "order": 1, "title": 1, "step_type": 1},
        ).sort([("survey_id", 1), ("order", 1)]).to_list(2000)
        steps_by_survey: dict[str, list[SubmissionStep]] = {}
        for document in step_documents:
            steps_by_survey.setdefault(str(document.get("survey_id") or ""), []).append(
                submission_step_from_document(document),
            )

        progress_documents = await self._db.user_progress.find(
            {"user_id": {"$in": list(user_ids)}},
            {"_id": 0, "user_id": 1, "step_id": 1, "status": 1, "completed_at": 1},
        ).to_list(max(1000, len(user_ids) * 100))
        progress_by_user: dict[str, dict[str, SubmissionProgress]] = {}
        for document in progress_documents:
            progress = submission_progress_from_document(document)
            progress_by_user.setdefault(str(document.get("user_id") or ""), {})[
                progress.step_id
            ] = progress

        return SubmissionContext(
            survey_by_user=survey_by_user,
            steps_by_survey={key: tuple(value) for key, value in steps_by_survey.items()},
            progress_by_user=progress_by_user,
        )
