"""Application service for partner submission completion resolution."""
from __future__ import annotations

from typing import Any

from slices.partner_submissions.domain import submission_work_statuses
from slices.partner_submissions.mappers import submission_from_document
from slices.partner_submissions.ports import PartnerSubmissionRepository


class PartnerSubmissionService:
    def __init__(self, repository: PartnerSubmissionRepository) -> None:
        self._repository = repository

    async def work_statuses(
        self, documents: list[dict[str, Any]],
    ) -> dict[tuple[str, str], dict[str, object]]:
        submissions = tuple(submission_from_document(document) for document in documents)
        user_ids = tuple(dict.fromkeys(row.user_id for row in submissions if row.user_id))
        if not user_ids:
            return {}
        context = await self._repository.load_context(user_ids)
        return {
            key: status.to_dict()
            for key, status in submission_work_statuses(submissions, context).items()
        }
