"""Typed values used by partner administration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class PartnerUpdatePlan:
    fields: Mapping[str, Any]
    survey_ids: tuple[str, ...] | None
    priced_step_ids: tuple[str, ...] | None


@dataclass(frozen=True, slots=True)
class PartnerDeletion:
    partner_id: str
    partner_name: str
    user_ids: tuple[str, ...]
