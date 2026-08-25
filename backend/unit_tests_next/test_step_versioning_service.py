from __future__ import annotations

import asyncio
from typing import Any

from slices.step_versioning.service import StepVersioningService


class Repository:
    def __getattr__(self, name: str) -> Any:
        async def call(*args: Any, **kwargs: Any) -> Any:
            results = {
                "insert_step_version": {"version": 2}, "ensure_step_version": 2,
                "update_step_versioned": (1, 2, {"updated": True}), "bind_revision_documents": 3,
                "write_progress_revision": {"revision": 4},
                "migrate": {"steps": 1, "answers": 2, "documents": 3},
                "revision_view": [{"user_id": "u"}],
            }
            return results[name]
        return call


def test_service_delegates_the_complete_use_case_boundary():
    async def scenario() -> None:
        service = StepVersioningService(Repository())
        assert (await service.insert_step_version({}, 2, None, "update"))["version"] == 2
        assert await service.ensure_step_version({}) == 2
        assert (await service.update_step_versioned({}, {}, [], {}, "update"))[1] == 2
        assert await service.bind_revision_documents({}) == 3
        revision = await service.write_progress_revision(
            user_id="u", step={}, status="active", data=None, actor=None, change_type="start",
        )
        assert revision["revision"] == 4 and (await service.migrate())["answers"] == 2
        assert (await service.revision_view("u"))[0]["user_id"] == "u"
    asyncio.run(scenario())
