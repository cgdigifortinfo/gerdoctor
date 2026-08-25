"""Ports required by the partner user workspace service."""
from __future__ import annotations

from typing import Protocol

from slices.partner_workspace.models import WorkspaceProgress, WorkspaceStep, WorkspaceUser


class PartnerWorkspaceRepository(Protocol):
    async def find_user(self, user_id: str) -> WorkspaceUser | None: ...

    async def load_progress(self, user_id: str, survey_id: str | None) -> tuple[WorkspaceProgress, ...]: ...

    async def load_steps(self, survey_id: str | None) -> tuple[WorkspaceStep, ...]: ...
