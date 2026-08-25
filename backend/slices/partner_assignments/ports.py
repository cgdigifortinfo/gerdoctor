"""Typed persistence port for partner assignment contexts."""
from __future__ import annotations

from typing import Protocol

from slices.partner_assignments.models import AssignmentContext


class PartnerAssignmentRepository(Protocol):
    async def load_context(self, user_ids: tuple[str, ...]) -> AssignmentContext: ...
