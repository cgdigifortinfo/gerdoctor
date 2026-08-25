"""MongoDB read model for partner dashboard analytics."""
from __future__ import annotations

from typing import Any

from infrastructure.mongo_ids import object_id_or_none

from slices.partner_insights.mappers import (
    insight_partner_from_document,
    insight_profile_from_document,
    insight_submission_from_document,
)
from slices.partner_insights.models import InsightProfile, InsightSnapshot


class MongoPartnerInsightsRepository:
    def __init__(self, database: Any) -> None:
        self._db = database

    async def load_snapshot(self, partner_id: str) -> InsightSnapshot:
        partner_document = await self._db.partners.find_one({"_id": object_id_or_none(partner_id)})
        partner = insight_partner_from_document(partner_document)
        submission_documents = await self._db.partner_submissions.find(
            {"partner_id": partner_id}, {"_id": 0},
        ).to_list(5000)
        submissions = tuple(insight_submission_from_document(row) for row in submission_documents)
        user_ids = partner.linked_user_ids | frozenset(row.user_id for row in submissions if row.user_id)

        accepted_user_ids: set[str] = set()
        profiles_by_user: dict[str, InsightProfile] = {}
        if user_ids:
            async for progress in self._db.user_progress.find({
                "user_id": {"$in": list(user_ids)},
                "status": {"$in": ["completed", "in_progress"]},
                "step_order": {"$gt": 1},
            }, {"user_id": 1}):
                accepted_user_ids.add(str(progress["user_id"]))
            async for progress in self._db.user_progress.find({
                "user_id": {"$in": list(user_ids)}, "step_order": 1,
            }, {"user_id": 1, "data": 1}):
                profiles_by_user[str(progress["user_id"])] = insight_profile_from_document(
                    progress.get("data") or {},
                )
        return InsightSnapshot(
            partner=partner,
            submissions=submissions,
            accepted_user_ids=frozenset(accepted_user_ids),
            profiles_by_user=profiles_by_user,
        )
