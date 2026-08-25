"""Persistence port for loading survey runtime contexts."""
from __future__ import annotations

from typing import Protocol

from slices.survey_runtime.models import SurveyRuntimeContext


class SurveyRuntimeRepository(Protocol):
    async def load(self, user_id: str) -> SurveyRuntimeContext: ...

    async def load_many(self, user_ids: tuple[str, ...]) -> dict[str, SurveyRuntimeContext]: ...
