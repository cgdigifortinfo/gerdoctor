"""Read and bulk-write use cases for administrative step configuration."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime
from typing import Any, Protocol, cast

from infrastructure.mongo_ids import object_id_or_none


class StepAdministrationNotFound(LookupError):
    pass


class StepAdministrationInvalidId(ValueError):
    pass


VersionUpdate = Callable[..., Awaitable[tuple[int, int, Mapping[str, Any]]]]
EnsureVersion = Callable[[Any, Mapping[str, Any]], Awaitable[Any]]


class StepAdministrationRepository(Protocol):
    async def steps(self, survey_id: str | None, include_deleted: bool) -> list[dict[str, Any]]: ...
    async def find(self, step_id: str, include_deleted: bool = True) -> dict[str, Any] | None: ...
    async def versions(self, step: Mapping[str, Any]) -> list[dict[str, Any]]: ...
    async def versioned_update(
        self, step: Mapping[str, Any], fields: Mapping[str, Any], actor: Mapping[str, Any],
        change_type: str,
    ) -> tuple[int, int]: ...


class MongoStepAdministrationRepository:
    def __init__(
        self, database: Any, ensure_version: EnsureVersion, update_versioned: VersionUpdate,
    ) -> None:
        self._database = database
        self._ensure_version = ensure_version
        self._update_versioned = update_versioned

    async def steps(self, survey_id: str | None, include_deleted: bool) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if survey_id is not None:
            query["survey_id"] = survey_id
        if not include_deleted:
            query["is_deleted"] = {"$ne": True}
        return cast(list[dict[str, Any]], await self._database.steps.find(query).sort(
            "order", 1,
        ).to_list(100))

    async def find(self, step_id: str, include_deleted: bool = True) -> dict[str, Any] | None:
        object_id = object_id_or_none(step_id)
        if object_id is None:
            return None
        query: dict[str, Any] = {"_id": object_id}
        if not include_deleted:
            query["is_deleted"] = {"$ne": True}
        return cast(dict[str, Any] | None, await self._database.steps.find_one(query))

    async def versions(self, step: Mapping[str, Any]) -> list[dict[str, Any]]:
        await self._ensure_version(self._database, step)
        return cast(list[dict[str, Any]], await self._database.step_versions.find(
            {"step_id": str(step["_id"])}, {"_id": 0},
        ).sort("version", -1).to_list(1000))

    async def versioned_update(
        self, step: Mapping[str, Any], fields: Mapping[str, Any], actor: Mapping[str, Any],
        change_type: str,
    ) -> tuple[int, int]:
        before, after, _ = await self._update_versioned(
            self._database, dict(step), dict(fields), [], dict(actor), change_type,
        )
        return before, after


class StepAdministrationService:
    def __init__(
        self, repository: StepAdministrationRepository, now: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._now = now

    async def steps(self, survey_id: str | None, include_deleted: bool) -> list[dict[str, Any]]:
        return await self._repository.steps(survey_id, include_deleted)

    async def versions(self, step_id: str) -> list[dict[str, Any]]:
        if object_id_or_none(step_id) is None:
            raise StepAdministrationInvalidId(step_id)
        step = await self._repository.find(step_id)
        if step is None:
            raise StepAdministrationNotFound(step_id)
        return await self._repository.versions(step)

    async def reorder(
        self, step_ids: list[str], survey_id: str | None, actor: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        changes = []
        for order, step_id in enumerate(step_ids, 1):
            step = await self._repository.find(step_id)
            if step is None or (survey_id is not None and step.get("survey_id") != survey_id):
                continue
            if step.get("order") == order:
                continue
            before, after = await self._repository.versioned_update(
                step, {"order": order}, actor, "reorder",
            )
            changes.append({"step_id": step_id, "before_version": before, "after_version": after})
        return changes

    async def save_layout(
        self, positions: Mapping[str, Mapping[str, float]], actor: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        changes = []
        for step_id, position in positions.items():
            step = await self._repository.find(step_id, include_deleted=False)
            normalized = {"x": position["x"], "y": position["y"]}
            if step is None or step.get("flow_position") == normalized:
                continue
            before, after = await self._repository.versioned_update(
                step, {"flow_position": normalized}, actor, "layout",
            )
            changes.append({"step_id": step_id, "before_version": before, "after_version": after})
        return changes

    async def archive(
        self, step_id: str, actor: Mapping[str, Any],
    ) -> tuple[dict[str, Any], int | None, int | None]:
        step = await self._repository.find(step_id)
        if step is None:
            raise StepAdministrationNotFound(step_id)
        if step.get("is_deleted"):
            return step, None, None
        before, after = await self._repository.versioned_update(step, {
            "is_deleted": True,
            "is_active": False,
            "deleted_at": self._now().isoformat(),
            "deleted_by": dict(actor),
        }, actor, "delete")
        return step, before, after
