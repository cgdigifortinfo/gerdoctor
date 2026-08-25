"""Application service for writing and reading audit entries."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from slices.audit_trail.domain import audit_entry, audit_query, normalized_pagination
from slices.audit_trail.models import AuditPage
from slices.audit_trail.ports import AuditTrailRepository


class AuditTrailService:
    def __init__(self, repository: AuditTrailRepository, now: Callable[[], str]) -> None:
        self._repository, self._now = repository, now

    async def record(self, actor_id: object, actor_email: object, action: str,
                     target_type: str, target_id: object = "",
                     details: Mapping[str, Any] | None = None) -> None:
        await self._repository.append(audit_entry(
            actor_id, actor_email, action, target_type, target_id, details, self._now(),
        ))

    async def page(self, limit: int = 100, skip: int = 0, action: str = "",
                   date_from: str = "", date_to: str = "") -> AuditPage:
        normalized_limit, normalized_skip = normalized_pagination(limit, skip)
        return await self._repository.page(
            audit_query(action, date_from, date_to), normalized_limit, normalized_skip,
        )

    async def initialize(self) -> None:
        await self._repository.ensure_indexes()
