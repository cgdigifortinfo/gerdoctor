"""Immutable value objects for step versions and answer revisions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ProgressRevisionPlan:
    """Documents required to atomically advance one user's step answer."""

    current: Mapping[str, Any]
    revision: Mapping[str, Any]
    unset_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MigrationStats:
    steps: int = 0
    answers: int = 0
    documents: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "steps": self.steps,
            "answers": self.answers,
            "documents": self.documents,
        }
