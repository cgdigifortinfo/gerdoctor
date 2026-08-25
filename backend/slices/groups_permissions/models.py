"""Immutable values used by groups and permissions rules."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PermissionInputs:
    group_permissions: tuple[str, ...]
    allowed: tuple[str, ...]
    denied: tuple[str, ...]
    administrator: bool = False


@dataclass(frozen=True, slots=True)
class GroupCreate:
    name: str
    description: str
    role: str
    permissions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GroupUpdate:
    name: str | None = None
    description: str | None = None
    role: str | None = None
    permissions: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class GroupUpdatePlan:
    fields: dict[str, object]
    role: str
    role_changed: bool
