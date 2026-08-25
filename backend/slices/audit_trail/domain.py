"""Pure audit-entry and query rules."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from slices.audit_trail.models import AuditEntry


def audit_entry(actor_id: object, actor_email: object, action: str,
                target_type: str, target_id: object, details: Mapping[str, Any] | None,
                timestamp: str) -> AuditEntry:
    return AuditEntry(str(actor_id), str(actor_email), action, target_type,
                      str(target_id), dict(details or {}), timestamp)


def audit_query(action: str = "", date_from: str = "", date_to: str = "") -> dict[str, Any]:
    query: dict[str, Any] = {}
    if action:
        query["action"] = action
    timestamp: dict[str, str] = {}
    if date_from:
        timestamp["$gte"] = date_from
    if date_to:
        timestamp["$lte"] = date_to
    if timestamp:
        query["timestamp"] = timestamp
    return query


def normalized_pagination(limit: int, skip: int) -> tuple[int, int]:
    return limit, max(skip, 0)
