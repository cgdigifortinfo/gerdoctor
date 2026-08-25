"""Typed, immutable values used by the partner user workspace."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class WorkspaceAction(str, Enum):
    COMPLETE = "complete"
    REJECT = "reject"


@dataclass(frozen=True, slots=True)
class WorkspaceUser:
    id: str
    name: str
    email: str
    survey_id: str | None
    notification_preferences: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class WorkspaceStep:
    id: str
    order: float
    title: str
    step_type: str
    filter_tag: str
    description: str
    document: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class WorkspaceProgress:
    step_id: str
    status: str
    revision: int | None
    data: Mapping[str, Any]
    document: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class PartnerWorkspace:
    user: WorkspaceUser
    steps: tuple[WorkspaceStep, ...]
    progress: tuple[WorkspaceProgress, ...]
    managed_step_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkspaceRevision:
    step_id: str
    revision: int | None
    changed_by_partner_id: str
    data: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class WorkspaceUpload:
    file_id: str
    filename: str
    document: Mapping[str, Any]
