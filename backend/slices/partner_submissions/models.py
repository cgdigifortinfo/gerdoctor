"""Immutable values for partner service submissions."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class SubmissionStepKind(str, Enum):
    MILESTONE = "milestone"
    DECISION = "decision"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class SubmissionStep:
    id: str
    order: float
    title: str
    kind: SubmissionStepKind


@dataclass(frozen=True, slots=True)
class SubmissionProgress:
    step_id: str
    status: str = "pending"
    completed_at: str | None = None


@dataclass(frozen=True, slots=True)
class PartnerSubmission:
    user_id: str
    service_step_id: str


@dataclass(frozen=True, slots=True)
class SubmissionWorkStatus:
    completed: bool
    completed_at: str | None
    milestone_step_id: str | None
    service_step_id: str
    service_step_title: str
    milestone_step_title: str

    def to_dict(self) -> dict[str, object]:
        return {
            "completed": self.completed,
            "completed_at": self.completed_at,
            "milestone_step_id": self.milestone_step_id,
            "service_step_id": self.service_step_id,
            "service_step_title": self.service_step_title,
            "milestone_step_title": self.milestone_step_title,
        }


@dataclass(frozen=True, slots=True)
class SubmissionContext:
    survey_by_user: Mapping[str, str]
    steps_by_survey: Mapping[str, tuple[SubmissionStep, ...]]
    progress_by_user: Mapping[str, Mapping[str, SubmissionProgress]]
