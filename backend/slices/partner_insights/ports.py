"""Typed ports used by partner insight aggregation."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from slices.partner_insights.models import InsightSnapshot, InsightSubmission


class PartnerInsightsRepository(Protocol):
    async def load_snapshot(self, partner_id: str) -> InsightSnapshot: ...


class SubmissionCompletionProvider(Protocol):
    async def completed(
        self, submissions: tuple[InsightSubmission, ...],
    ) -> Mapping[tuple[str, str], bool]: ...


class AssignmentCompletionProvider(Protocol):
    async def completed(
        self, user_ids: tuple[str, ...], partner_id: str, partner_name: str,
    ) -> Mapping[str, bool]: ...
