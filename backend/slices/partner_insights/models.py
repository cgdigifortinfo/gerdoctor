"""Immutable input values for partner dashboard analytics."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True, slots=True)
class InsightPartner:
    id: str
    name: str
    awaiting_assignment: bool
    linked_user_ids: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class InsightSubmission:
    user_id: str
    service_step_id: str
    submitted_at: str


@dataclass(frozen=True, slots=True)
class InsightProfile:
    specialty: str = "Unbekannt"
    state: str = "Unbekannt"


@dataclass(frozen=True, slots=True)
class InsightSnapshot:
    partner: InsightPartner
    submissions: tuple[InsightSubmission, ...]
    accepted_user_ids: frozenset[str]
    profiles_by_user: Mapping[str, InsightProfile]
