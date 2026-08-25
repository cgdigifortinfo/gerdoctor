"""Application service for partner dashboard analytics."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from slices.partner_insights.domain import build_partner_insights
from slices.partner_insights.ports import (
    AssignmentCompletionProvider,
    PartnerInsightsRepository,
    SubmissionCompletionProvider,
)


class PartnerInsightsService:
    def __init__(
        self,
        repository: PartnerInsightsRepository,
        submission_completion: SubmissionCompletionProvider,
        assignment_completion: AssignmentCompletionProvider,
        clock: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._submission_completion = submission_completion
        self._assignment_completion = assignment_completion
        self._clock = clock

    async def insights(self, partner_id: str) -> dict[str, Any]:
        snapshot = await self._repository.load_snapshot(partner_id)
        if snapshot.partner.awaiting_assignment:
            return build_partner_insights(snapshot, {}, {}, self._clock())
        user_ids = tuple(dict.fromkeys(
            [*snapshot.partner.linked_user_ids, *(row.user_id for row in snapshot.submissions if row.user_id)],
        ))
        submission_completed = await self._submission_completion.completed(snapshot.submissions)
        assignment_completed = await self._assignment_completion.completed(
            user_ids, snapshot.partner.id, snapshot.partner.name,
        )
        return build_partner_insights(
            snapshot, submission_completed, assignment_completed, self._clock(),
        )
