"""Application boundary for step and answer versioning."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from slices.step_versioning.ports import StepVersioningRepository


class StepVersioningService:
    def __init__(self, repository: StepVersioningRepository) -> None:
        self._repository = repository

    async def insert_step_version(self, step: Mapping[str, Any], version: int,
                                  actor: Mapping[str, Any] | None, change_type: str) -> dict[str, Any]:
        return await self._repository.insert_step_version(step, version, actor, change_type)

    async def ensure_step_version(self, step: Mapping[str, Any], actor: Mapping[str, Any] | None = None,
                                  change_type: str = "migration") -> int:
        return await self._repository.ensure_step_version(step, actor, change_type)

    async def update_step_versioned(self, step: Mapping[str, Any], set_fields: Mapping[str, Any],
                                    unset_fields: Sequence[str] | None, actor: Mapping[str, Any],
                                    change_type: str) -> tuple[int, int, dict[str, Any]]:
        return await self._repository.update_step_versioned(step, set_fields, unset_fields, actor, change_type)

    async def bind_revision_documents(self, revision: Mapping[str, Any]) -> int:
        return await self._repository.bind_revision_documents(revision)

    async def write_progress_revision(self, *, user_id: str, step: Mapping[str, Any], status: str,
                                      data: Mapping[str, Any] | None, actor: Mapping[str, Any] | None,
                                      change_type: str, extra_fields: Mapping[str, Any] | None = None,
                                      unset_fields: Sequence[str] | None = None) -> dict[str, Any]:
        return await self._repository.write_progress_revision(
            user_id=user_id, step=step, status=status, data=data, actor=actor, change_type=change_type,
            extra_fields=extra_fields, unset_fields=unset_fields,
        )

    async def migrate(self) -> dict[str, int]:
        return await self._repository.migrate()

    async def revision_view(self, user_id: str) -> list[dict[str, Any]]:
        return await self._repository.revision_view(user_id)
