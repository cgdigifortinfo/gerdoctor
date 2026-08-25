"""Ports used by the partner selection application service."""
from __future__ import annotations

from typing import Protocol

from slices.partner_selection.models import SelectablePartner, SelectionStep


class PartnerSelectionRepository(Protocol):
    async def find_step(self, step_id: str) -> SelectionStep | None: ...

    async def find_partners(self, partner_ids: tuple[str, ...]) -> tuple[SelectablePartner, ...]: ...

    async def list_active_partners(self, tag: str) -> tuple[SelectablePartner, ...]: ...
