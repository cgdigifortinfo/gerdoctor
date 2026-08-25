from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from slices.survey_runtime.mappers import runtime_context_from_documents
from slices.survey_runtime.service import SurveyRuntimeService


class Repository:
    def __init__(self) -> None:
        self.context_value = runtime_context_from_documents([{"_id": "s", "order": 1}], [])

    async def load(self, user_id: str):  # type: ignore[no-untyped-def]
        assert user_id == "u"
        return self.context_value

    async def load_many(self, user_ids: tuple[str, ...]):  # type: ignore[no-untyped-def]
        return {user_id: self.context_value for user_id in user_ids}


def test_service_exposes_context_visibility_planning_and_metrics() -> None:
    asyncio.run(assert_service())


async def assert_service() -> None:
    repository = Repository()
    service = SurveyRuntimeService(repository, lambda: datetime(2024, 1, 1, tzinfo=timezone.utc))
    assert await service.context("u") is repository.context_value
    assert not (await service.visibility("u")).hidden_step_ids
    assert await service.auto_complete_step_ids("u") == ()
    assert (await service.metrics("u")).completion_pct == 0
    assert set(await service.metrics_many(("u", "v"))) == {"u", "v"}
