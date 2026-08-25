"""Administrative partner list read model."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, cast

from slices.partner_administration.domain import (
    partner_admin_record,
    service_steps_for_partner,
    sorted_partner_records,
)


class PartnerAdministrationListingRepository(Protocol):
    async def partners(self) -> list[dict[str, Any]]: ...
    async def users(self) -> list[dict[str, Any]]: ...
    async def submissions(self) -> list[dict[str, Any]]: ...
    async def service_steps(self) -> list[dict[str, Any]]: ...


class MongoPartnerAdministrationListingRepository:
    def __init__(self, database: Any) -> None:
        self._database = database

    async def partners(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], await self._database.partners.find().to_list(1000))

    async def users(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], await self._database.users.find(
            {}, {"password_hash": 0},
        ).to_list(2000))

    async def submissions(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], await self._database.partner_submissions.find(
            {}, {"partner_id": 1, "user_id": 1},
        ).to_list(20000))

    async def service_steps(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], await self._database.steps.find({
            "step_type": {"$in": ["partner_selection", "partner_multiselection"]},
            "is_active": True,
        }, {
            "title": 1, "order": 1, "survey_id": 1, "filter_tag": 1,
            "partner_user_fee_cents": 1,
        }).sort("order", 1).to_list(1000))


WorkStatuses = Callable[
    [list[str], str, str], Awaitable[dict[str, dict[str, Any]]],
]


class PartnerAdministrationListingService:
    def __init__(
        self,
        repository: PartnerAdministrationListingRepository,
        work_statuses: WorkStatuses,
    ) -> None:
        self._repository = repository
        self._work_statuses = work_statuses

    async def list(self) -> list[dict[str, Any]]:
        partners = sorted_partner_records(await self._repository.partners())
        users = await self._repository.users()
        submissions = await self._repository.submissions()
        steps = await self._repository.service_steps()
        user_by_id = {str(user["_id"]): user for user in users}
        dashboard_user_by_partner = {
            str(user["partner_id"]): user
            for user in users
            if user.get("role") == "partner" and user.get("partner_id")
        }
        submissions_by_partner: dict[str, list[dict[str, Any]]] = {}
        for submission in submissions:
            partner_id = submission.get("partner_id")
            if partner_id:
                submissions_by_partner.setdefault(str(partner_id), []).append(submission)

        pending_by_partner: dict[str, int] = {}
        for partner in partners:
            partner_id = str(partner["_id"])
            candidate_ids = {
                str(item["user_id"])
                for item in submissions_by_partner.get(partner_id, [])
                if item.get("user_id")
            }
            candidate_ids.update(str(value) for value in partner.get("linked_user_ids") or [])
            statuses = await self._work_statuses(
                list(candidate_ids), partner_id, str(partner.get("name", "")),
            )
            pending_by_partner[partner_id] = sum(
                not statuses.get(user_id, {}).get("completed", False)
                for user_id in candidate_ids
            )

        result = []
        for partner in partners:
            partner_id = str(partner["_id"])
            linked_ids = [str(value) for value in partner.get("linked_user_ids") or []]
            linked_users = [
                {"id": user_id, "name": user_by_id[user_id]["name"],
                 "email": user_by_id[user_id]["email"]}
                for user_id in linked_ids
                if user_id in user_by_id
            ]
            dashboard_user = dashboard_user_by_partner.get(partner_id)
            if dashboard_user is not None and str(dashboard_user["_id"]) not in linked_ids:
                linked_users.insert(0, {
                    "id": str(dashboard_user["_id"]),
                    "name": dashboard_user["name"],
                    "email": dashboard_user["email"],
                })
            result.append(partner_admin_record(
                partner,
                linked_users,
                pending_by_partner.get(partner_id, 0),
                service_steps_for_partner(partner, steps),
            ))
        return result
