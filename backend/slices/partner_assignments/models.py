"""Immutable values for partner-to-survey-step assignments."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class StepKind(str, Enum):
    PARTNER_SELECTION = "partner_selection"
    PARTNER_MULTI_SELECTION = "partner_multiselection"
    MILESTONE = "milestone"
    DECISION = "decision"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class FlowStep:
    id: str
    order: float
    kind: StepKind


@dataclass(frozen=True, slots=True)
class StepProgress:
    step_id: str
    status: str = "pending"
    selected_partner_ids: frozenset[str] = field(default_factory=frozenset)
    selected_partner_name: str = ""
    completed_at: str | None = None


@dataclass(frozen=True, slots=True)
class PartnerWorkStatus:
    completed: bool = False
    completed_at: str | None = None
    milestone_step_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "completed": self.completed,
            "completed_at": self.completed_at,
            "milestone_step_id": self.milestone_step_id,
        }


@dataclass(frozen=True, slots=True)
class AssignmentContext:
    steps_by_user: Mapping[str, tuple[FlowStep, ...]]
    progress_by_user: Mapping[str, tuple[StepProgress, ...]]
