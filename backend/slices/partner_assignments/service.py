"""Application service for bulk partner work status resolution."""
from __future__ import annotations

from slices.partner_assignments.domain import partner_work_status
from slices.partner_assignments.models import PartnerWorkStatus
from slices.partner_assignments.ports import PartnerAssignmentRepository


class PartnerAssignmentService:
    def __init__(self, repository: PartnerAssignmentRepository):
        self._repository = repository

    async def work_statuses(
        self, user_ids: list[str], partner_id: str, partner_name: str,
    ) -> dict[str, PartnerWorkStatus]:
        unique_ids = tuple(dict.fromkeys(user_id for user_id in user_ids if user_id))
        if not unique_ids:
            return {}
        context = await self._repository.load_context(unique_ids)
        return {
            user_id: partner_work_status(
                context.steps_by_user.get(user_id, ()),
                context.progress_by_user.get(user_id, ()),
                partner_id,
                partner_name,
            )
            for user_id in unique_ids
        }
