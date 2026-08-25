"""Typed persistence port for partner submission contexts."""
from __future__ import annotations

from typing import Protocol

from slices.partner_submissions.models import SubmissionContext


class PartnerSubmissionRepository(Protocol):
    async def load_context(self, user_ids: tuple[str, ...]) -> SubmissionContext: ...
