"""Immutable values used while evaluating a user's survey journey."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class RuntimeProgress:
    step_id: str
    status: str
    data: Mapping[str, Any]
    completed_at: str | None


@dataclass(frozen=True, slots=True)
class RuntimeStep:
    id: str
    order: float
    conditions: tuple[Mapping[str, Any], ...]
    duration_value: int
    duration_unit: str
    step_type: str
    document: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class SurveyRuntimeContext:
    steps: tuple[RuntimeStep, ...]
    progress: tuple[RuntimeProgress, ...]


@dataclass(frozen=True, slots=True)
class RuntimeVisibility:
    hidden_step_ids: frozenset[str]
    blocked_step_ids: frozenset[str]


@dataclass(frozen=True, slots=True)
class RuntimeMetrics:
    completion_pct: int
    estimated_completion: str | None

    def as_dict(self) -> dict[str, int | str | None]:
        return {
            "completion_pct": self.completion_pct,
            "estimated_completion": self.estimated_completion,
        }


OrderState = Mapping[float, Mapping[str, Any]]
Now = datetime
