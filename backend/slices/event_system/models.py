"""Immutable values used by the event dispatcher."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class HandlerDecision:
    status: str
    reason: str = ""
    recipient: str = ""
    template_key: str = ""
    user_id: str = ""
    channels: tuple[str, ...] = ()
    provider: str = "unconfigured"


@dataclass(frozen=True, slots=True)
class EventOutcome:
    status: str
    error: str
    handler_results: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class EventPage:
    events: tuple[dict[str, Any], ...]
    total: int

    def to_document(self) -> dict[str, Any]:
        return {"events": list(self.events), "total": self.total}
