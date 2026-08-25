"""Injectable system-clock adapter."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...

    def now_iso(self) -> str: ...


class SystemUtcClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def now_iso(self) -> str:
        return self.now().isoformat()


system_utc_clock = SystemUtcClock()
