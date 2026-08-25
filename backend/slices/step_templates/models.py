"""Immutable commands and results for step templates."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TemplateDraft:
    name: str
    description: str
    config: dict[str, Any]


@dataclass(frozen=True, slots=True)
class AppliedTemplate:
    step_id: str
    survey_id: str
