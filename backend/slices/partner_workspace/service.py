"""Application service for loading a partner's per-user workspace."""
from __future__ import annotations

from slices.partner_assignments.domain import managed_step_ids
from slices.partner_assignments.mappers import flow_step_from_document, progress_from_document
from slices.partner_workspace.models import PartnerWorkspace
from slices.partner_workspace.ports import PartnerWorkspaceRepository


class WorkspaceUserNotFound(LookupError):
    pass


class PartnerWorkspaceService:
    def __init__(self, repository: PartnerWorkspaceRepository) -> None:
        self._repository = repository

    async def load(self, user_id: str, partner_id: str, partner_name: str) -> PartnerWorkspace:
        user = await self._repository.find_user(user_id)
        if user is None:
            raise WorkspaceUserNotFound(user_id)
        progress = await self._repository.load_progress(user_id, user.survey_id)
        steps = await self._repository.load_steps(user.survey_id)
        managed = managed_step_ids(
            tuple(flow_step_from_document({
                **step.document, "id": step.id, "order": step.order, "step_type": step.step_type,
            }) for step in steps),
            tuple(progress_from_document({
                **row.document, "step_id": row.step_id, "status": row.status, "data": row.data,
            }) for row in progress),
            partner_id,
            partner_name,
        )
        return PartnerWorkspace(user=user, steps=steps, progress=progress, managed_step_ids=managed)
