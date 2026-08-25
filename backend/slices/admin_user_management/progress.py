"""Administrative progress updates for a survey user."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Protocol

from infrastructure.mongo_ids import object_id_or_none


class AdminProgressStepNotFound(LookupError):
    """Raised when an administrator addresses a missing survey step."""


class MongoAdminProgressRepository:
    def __init__(self, database: Any) -> None:
        self._database = database

    async def step(self, step_id: str) -> dict[str, Any] | None:
        object_id = object_id_or_none(step_id)
        if object_id is None:
            return None
        result = await self._database.steps.find_one({"_id": object_id})
        return result if isinstance(result, dict) else None


class AdminProgressRepository(Protocol):
    async def step(self, step_id: str) -> dict[str, Any] | None: ...


ProgressWriter = Callable[..., Awaitable[Any]]
StatusSkipper = Callable[[str, str], Awaitable[Any]]
AutoCompleter = Callable[[str], Awaitable[Any]]


class AdminUserProgressService:
    def __init__(
        self,
        repository: AdminProgressRepository,
        write_revision: ProgressWriter,
        apply_status_skips: StatusSkipper,
        apply_auto_completes: AutoCompleter,
    ) -> None:
        self._repository = repository
        self._write_revision = write_revision
        self._apply_status_skips = apply_status_skips
        self._apply_auto_completes = apply_auto_completes

    async def update(
        self,
        user_id: str,
        step_id: str,
        status: str,
        data: Mapping[str, Any] | None,
        actor: Mapping[str, Any],
    ) -> None:
        step = await self._repository.step(step_id)
        if step is None:
            raise AdminProgressStepNotFound(step_id)
        progress_data = dict(data or {})
        await self._write_revision(
            user_id=user_id,
            step=step,
            status=status,
            data=progress_data,
            actor={
                "id": str(actor["_id"]),
                "email": str(actor["email"]),
                "role": "admin",
            },
            change_type="admin_update",
        )
        recognition_status = progress_data.get("anerkennungsstatus")
        if step.get("order") == 1 and recognition_status:
            await self._apply_status_skips(user_id, str(recognition_status))
        await self._apply_auto_completes(user_id)
