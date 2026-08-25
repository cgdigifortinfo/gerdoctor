"""Mongo read adapter for administrative reporting."""
from __future__ import annotations

from datetime import datetime
from typing import Any, cast


class MongoAdminReportingRepository:
    def __init__(self, database: Any) -> None:
        self._database = database

    async def summary_counts(self, recent_since: datetime) -> dict[str, int]:
        return {
            "total_users": int(await self._database.users.count_documents({"role": "user"})),
            "total_partners": int(await self._database.partners.count_documents({"is_active": True})),
            "total_submissions": int(await self._database.partner_submissions.count_documents({})),
            "admin_count": int(await self._database.users.count_documents({"role": "admin"})),
            "partner_count": int(await self._database.users.count_documents({"role": "partner"})),
            "recent_registrations": int(await self._database.users.count_documents({
                "created_at": {"$gte": recent_since.isoformat()},
            })),
        }

    async def active_steps(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], await self._database.steps.find({
            "is_active": True,
        }).sort("order", 1).to_list(100))

    async def step_counts(self, step_id: str) -> tuple[int, int, int]:
        total = int(await self._database.user_progress.count_documents({"step_id": step_id}))
        completed = int(await self._database.user_progress.count_documents({
            "step_id": step_id, "status": "completed",
        }))
        in_progress = int(await self._database.user_progress.count_documents({
            "step_id": step_id, "status": "in_progress",
        }))
        return total, completed, in_progress

    async def billing_partners(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], await self._database.partners.find({}, {
            "name": 1, "stripe_customer_id": 1, "billing_status": 1,
        }).sort("name", 1).to_list(1000))
