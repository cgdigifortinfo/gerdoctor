"""Application services for admin-managed partner organizations."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from slices.partner_administration.domain import create_partner_document, partner_update_plan, user_role_update
from slices.partner_administration.models import PartnerDeletion
from slices.partner_administration.ports import PartnerAdministrationRepository


class PartnerAdministrationError(ValueError): pass
class UnknownPartner(PartnerAdministrationError): pass
class UnknownUser(PartnerAdministrationError): pass
class UnknownSurvey(PartnerAdministrationError): pass
class InvalidPricedStep(PartnerAdministrationError): pass


class PartnerAdministrationService:
    def __init__(self, repository: PartnerAdministrationRepository) -> None:
        self._repository = repository

    async def create(self, data: Mapping[str, Any], created_at: str) -> str:
        return await self._repository.insert(create_partner_document(data, created_at))

    async def update(self, partner_id: str, data: Mapping[str, Any], updated_at: str) -> dict[str, Any]:
        plan = partner_update_plan(data, updated_at)
        if plan.survey_ids is not None:
            valid = await self._repository.valid_survey_count(plan.survey_ids)
            if valid != len(plan.survey_ids):
                raise UnknownSurvey
        if plan.priced_step_ids is not None:
            valid = await self._repository.valid_priced_step_count(plan.priced_step_ids)
            if valid != len(plan.priced_step_ids):
                raise InvalidPricedStep
        updated = await self._repository.update(partner_id, plan.fields)
        if updated is None:
            raise UnknownPartner(partner_id)
        return updated

    async def delete(self, partner_id: str, user_group_id: str | None) -> PartnerDeletion:
        partner = await self._repository.find(partner_id)
        if partner is None:
            raise UnknownPartner(partner_id)
        users = await self._repository.users_for_partner(partner_id)
        for user in users:
            await self._repository.set_user_role(
                str(user["_id"]), user_role_update("user", user_group_id), remove_partner=True,
            )
        await self._repository.delete(partner_id)
        return PartnerDeletion(partner_id, str(partner["name"]), tuple(str(user["_id"]) for user in users))

    async def link_user(self, partner_id: str, user_id: str, user_group_id: str | None,
                        partner_group_id: str | None) -> str:
        target = await self._repository.find_user(user_id)
        if target is None:
            raise UnknownUser(user_id)
        partner = await self._repository.find(partner_id)
        if partner is None:
            raise UnknownPartner(partner_id)
        previous = partner.get("user_id")
        if previous:
            await self._repository.set_user_role(
                str(previous), user_role_update("user", user_group_id), remove_partner=True,
            )
        await self._repository.set_primary_user(partner_id, user_id)
        await self._repository.set_user_role(
            user_id, user_role_update("partner", partner_group_id, partner_id), remove_partner=False,
        )
        return str(target["name"])

    async def unlink_user(self, partner_id: str, user_group_id: str | None) -> None:
        partner = await self._repository.find(partner_id)
        if partner is None:
            raise UnknownPartner(partner_id)
        previous = partner.get("user_id")
        if previous:
            await self._repository.set_user_role(
                str(previous), user_role_update("user", user_group_id), remove_partner=True,
            )
        await self._repository.set_primary_user(partner_id, None)
