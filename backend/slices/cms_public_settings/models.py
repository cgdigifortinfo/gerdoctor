"""Immutable values used by the CMS/public-settings slice."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CmsPayload:
    content: dict[str, Any]
    translations: dict[str, Any]

    def response(self) -> dict[str, dict[str, Any]]:
        return {"content": dict(self.content), "translations": dict(self.translations)}
