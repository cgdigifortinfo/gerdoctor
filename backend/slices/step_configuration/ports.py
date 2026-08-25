"""Persistence port for versioned step configuration changes."""
from __future__ import annotations

from typing import Any, Mapping, Protocol


class StepConfigurationRepository(Protocol):
    async def create(self, values: Mapping[str, Any], actor: Mapping[str, Any]) -> str: ...
    async def update(
        self, step_id: str, values: Mapping[str, Any], unset_fields: tuple[str, ...],
        actor: Mapping[str, Any], change_type: str,
    ) -> tuple[int, int]: ...
    async def find(self, step_id: str, include_deleted: bool = False) -> Mapping[str, Any] | None: ...
