"""Immutable values for validated step configuration changes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class StepConfigurationChange:
    values: Mapping[str, Any]
    unset_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StepRelationIssue:
    step_order: float
    step_title: str
    message: str

    def text(self) -> str:
        return f"#{self.step_order:g} {self.step_title}: {self.message}"
