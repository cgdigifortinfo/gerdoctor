"""Application service for validated partner-selection plans."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from slices.partner_selection.domain import build_selection_plan, sorted_partner_documents
from slices.partner_selection.models import PartnerSelectionPlan, SelectionUser
from slices.partner_selection.ports import PartnerSelectionRepository


class PartnerSelectionService:
    def __init__(self, repository: PartnerSelectionRepository) -> None:
        self._repository = repository

    async def prepare(
        self, *, user: SelectionUser, step_id: str | None, partner_ids: Iterable[str],
        data: Mapping[str, Any] | None, multiple: bool,
    ) -> PartnerSelectionPlan:
        requested = tuple(partner_ids)
        step = await self._repository.find_step(step_id) if step_id is not None else None
        partners = await self._repository.find_partners(tuple(dict.fromkeys(requested)))
        return build_selection_plan(
            user=user, requested_step_id=step_id, step=step,
            requested_partner_ids=requested, partners=partners, data=data, multiple=multiple,
        )

    async def list_partners(self, tag: str) -> tuple[Mapping[str, Any], ...]:
        partners = await self._repository.list_active_partners(tag)
        return sorted_partner_documents(partners)
