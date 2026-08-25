"""Partner-visible user detail read model."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from slices.partner_workspace.domain import (
    partner_selection_step_id, revision_is_visible, sanitize_progress,
)
from slices.partner_workspace.mappers import workspace_revision_from_document
from slices.partner_workspace.read_service import PartnerNotLinked, PartnerWorkspaceReadRepository
from slices.partner_workspace.service import PartnerWorkspaceService


class PartnerWorkspaceDetailService:
    def __init__(
        self, workspace: PartnerWorkspaceService, repository: PartnerWorkspaceReadRepository,
        revisions: Callable[[str], Awaitable[list[dict[str, Any]]]],
        completion: Callable[[str], Awaitable[int]],
        visible_email: Callable[[Mapping[str, Any], Mapping[str, Any] | None, str], Awaitable[str]],
    ) -> None:
        self._workspace, self._repo = workspace, repository
        self._revisions, self._completion, self._email = revisions, completion, visible_email

    async def detail(self, actor: Mapping[str, Any], user_id: str) -> dict[str, Any]:
        partner_id_value = actor.get("partner_id")
        if not partner_id_value: raise PartnerNotLinked
        partner_id = str(partner_id_value)
        partner = await self._repo.partner(partner_id)
        partner_name = str((partner or {}).get("name") or "")
        workspace = await self._workspace.load(user_id, partner_id, partner_name)
        revisions = await self._revisions(user_id)
        markers = {(row["step_id"], row["revision"]): row for row in revisions}
        managed = list(workspace.managed_step_ids)
        return {
            "id": workspace.user.id,
            "email": await self._email(actor, partner, workspace.user.email),
            "name": workspace.user.name,
            "progress": sanitize_progress(workspace.progress, workspace.steps, partner_id, markers),
            "steps": [{**step.document, "id": step.id} for step in workspace.steps],
            "completion_pct": await self._completion(user_id),
            "partner_step_id": partner_selection_step_id(
                workspace.steps, set((partner or {}).get("tags", [])),
            ),
            "partner_managed_step_ids": managed,
            "revisions": [row for row in revisions if revision_is_visible(
                workspace_revision_from_document(row), managed, partner_id, partner_name,
            )],
        }
