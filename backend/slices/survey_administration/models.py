"""Immutable survey commands."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True, slots=True)
class SurveyDraft:
    name: str
    slug: str
    description: str = ""
    audience: str = ""
    is_active: bool = True
    is_default: bool = False
    theme: dict[str, Any] | None = None
