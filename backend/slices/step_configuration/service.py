"""Application service for versioned Step Configuration commands."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Callable

from slices.step_configuration.domain import prepare_create, prepare_update
from slices.step_configuration.ports import StepConfigurationRepository


class StepConfigurationNotFound(Exception):
    pass


class StepConfigurationService:
    def __init__(
        self, repository: StepConfigurationRepository, now: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._now = now

    async def create(
        self, values: Mapping[str, Any], survey_id: str, actor: Mapping[str, Any],
    ) -> str:
        change = prepare_create(values, survey_id, self._now().isoformat())
        return await self._repository.create(change.values, actor)

    async def update(
        self, step_id: str, values: Mapping[str, Any], supplied_fields: frozenset[str],
        actor: Mapping[str, Any], change_type: str = "update",
    ) -> tuple[int, int]:
        change = prepare_update(values, supplied_fields)
        try:
            return await self._repository.update(
                step_id, change.values, change.unset_fields, actor, change_type,
            )
        except KeyError as error:
            raise StepConfigurationNotFound(step_id) from error
