"""Application service for consistent survey runtime evaluations."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from slices.survey_runtime.domain import auto_complete_step_ids, calculate_metrics, visibility
from slices.survey_runtime.models import RuntimeMetrics, RuntimeVisibility, SurveyRuntimeContext
from slices.survey_runtime.ports import SurveyRuntimeRepository


class SurveyRuntimeService:
    def __init__(self, repository: SurveyRuntimeRepository, now: Callable[[], datetime]) -> None:
        self._repository = repository
        self._now = now

    async def context(self, user_id: str) -> SurveyRuntimeContext:
        return await self._repository.load(user_id)

    async def visibility(self, user_id: str) -> RuntimeVisibility:
        return visibility(await self.context(user_id))

    async def auto_complete_step_ids(self, user_id: str) -> tuple[str, ...]:
        return auto_complete_step_ids(await self.context(user_id))

    async def metrics(self, user_id: str) -> RuntimeMetrics:
        return calculate_metrics(await self.context(user_id), self._now())

    async def metrics_many(self, user_ids: tuple[str, ...]) -> dict[str, RuntimeMetrics]:
        contexts = await self._repository.load_many(user_ids)
        current = self._now()
        return {user_id: calculate_metrics(context, current) for user_id, context in contexts.items()}
