"""Adapters from existing partner services to analytics completion ports."""
from __future__ import annotations

from collections.abc import Mapping

from slices.partner_insights.models import InsightSubmission
from slices.partner_assignments.service import PartnerAssignmentService
from slices.partner_submissions.service import PartnerSubmissionService


class SubmissionCompletionAdapter:
    def __init__(self, service: PartnerSubmissionService) -> None:
        self._service = service

    async def completed(
        self, submissions: tuple[InsightSubmission, ...],
    ) -> Mapping[tuple[str, str], bool]:
        statuses = await self._service.work_statuses([
            {"user_id": row.user_id, "step_id": row.service_step_id} for row in submissions
        ])
        return {key: bool(value["completed"]) for key, value in statuses.items()}


class AssignmentCompletionAdapter:
    def __init__(self, service: PartnerAssignmentService) -> None:
        self._service = service

    async def completed(
        self, user_ids: tuple[str, ...], partner_id: str, partner_name: str,
    ) -> Mapping[str, bool]:
        statuses = await self._service.work_statuses(list(user_ids), partner_id, partner_name)
        return {user_id: status.completed for user_id, status in statuses.items()}
