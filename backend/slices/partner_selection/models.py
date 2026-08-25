"""Immutable values for selecting one or more service partners."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class SelectionKind(str, Enum):
    SINGLE = "partner_selection"
    MULTIPLE = "partner_multiselection"


@dataclass(frozen=True, slots=True)
class SelectionUser:
    id: str
    survey_id: str | None


@dataclass(frozen=True, slots=True)
class SelectionStep:
    id: str
    kind: SelectionKind
    survey_id: str | None
    filter_tag: str
    document: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class SelectablePartner:
    id: str
    name: str
    tags: frozenset[str]
    active: bool
    document: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class PartnerSelectionPlan:
    step: SelectionStep | None
    partners: tuple[SelectablePartner, ...]
    selection_data: Mapping[str, Any]

    @property
    def partner_ids(self) -> tuple[str, ...]:
        return tuple(partner.id for partner in self.partners)
