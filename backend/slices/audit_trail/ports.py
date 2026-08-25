"""Persistence port for the audit trail."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from slices.audit_trail.models import AuditEntry, AuditPage


class AuditTrailRepository(Protocol):
    async def append(self, entry: AuditEntry) -> None: ...
    async def page(self, query: Mapping[str, Any], limit: int, skip: int) -> AuditPage: ...
    async def ensure_indexes(self) -> None: ...
