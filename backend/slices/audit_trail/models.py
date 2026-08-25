"""Immutable audit-trail values."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AuditEntry:
    actor_id: str
    actor_email: str
    action: str
    target_type: str
    target_id: str
    details: dict[str, Any]
    timestamp: str

    def to_document(self) -> dict[str, Any]:
        return {"actor_id": self.actor_id, "actor_email": self.actor_email,
                "action": self.action, "target_type": self.target_type,
                "target_id": self.target_id, "details": dict(self.details),
                "timestamp": self.timestamp}


@dataclass(frozen=True, slots=True)
class AuditPage:
    logs: tuple[dict[str, Any], ...]
    total: int
    action_types: tuple[str, ...]

    def to_document(self) -> dict[str, Any]:
        return {"logs": list(self.logs), "total": self.total,
                "action_types": list(self.action_types)}
