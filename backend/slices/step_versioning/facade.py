"""Compatibility facade for the Step Versioning / Answer History slice."""
from __future__ import annotations

from typing import Any

from infrastructure.clock import system_utc_clock
from slices.step_versioning.repository import MongoStepVersioningRepository
from slices.step_versioning.service import StepVersioningService


def utc_now() -> str:
    return system_utc_clock.now_iso()


def _service(db: Any) -> StepVersioningService:
    return StepVersioningService(MongoStepVersioningRepository(db, system_utc_clock))


async def insert_step_version(db: Any, step: dict[str, Any], version: int,
                              actor: dict[str, Any] | None, change_type: str) -> dict[str, Any]:
    return await _service(db).insert_step_version(step, version, actor, change_type)


async def ensure_step_version(db: Any, step: dict[str, Any], actor: dict[str, Any] | None = None,
                              change_type: str = "migration") -> int:
    return await _service(db).ensure_step_version(step, actor, change_type)


async def update_step_versioned(db: Any, step: dict[str, Any], set_fields: dict[str, Any],
                                unset_fields: list[str] | None, actor: dict[str, Any],
                                change_type: str) -> tuple[int, int, dict[str, Any]]:
    return await _service(db).update_step_versioned(step, set_fields, unset_fields, actor, change_type)


async def bind_revision_documents(db: Any, revision: dict[str, Any]) -> int:
    return await _service(db).bind_revision_documents(revision)


async def write_progress_revision(db: Any, **arguments: Any) -> dict[str, Any]:
    return await _service(db).write_progress_revision(**arguments)


async def migrate_step_answer_versioning(db: Any) -> dict[str, int]:
    return await _service(db).migrate()


async def revision_view(db: Any, user_id: str) -> list[dict[str, Any]]:
    return await _service(db).revision_view(user_id)
