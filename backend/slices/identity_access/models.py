"""Immutable identity values."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TokenIdentity:
    user_id: str
    email: str
    role: str

@dataclass(frozen=True, slots=True)
class RegisteredAccount:
    user_id: str
    user: dict[str, Any]
    partner_id: str | None = None
