"""Administrative analytics and billing report orchestration."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any, Protocol


class AdminReportingRepository(Protocol):
    async def summary_counts(self, recent_since: datetime) -> dict[str, int]: ...
    async def active_steps(self) -> list[dict[str, Any]]: ...
    async def step_counts(self, step_id: str) -> tuple[int, int, int]: ...
    async def billing_partners(self) -> list[dict[str, Any]]: ...


Invoices = Callable[[str], Awaitable[list[dict[str, Any]]]]
Usage = Callable[[str], Awaitable[dict[str, Any]]]


class AdminReportingService:
    def __init__(
        self, repository: AdminReportingRepository, invoices: Invoices,
        usage: Usage, now: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._invoices = invoices
        self._usage = usage
        self._now = now

    async def analytics(self) -> dict[str, Any]:
        result: dict[str, Any] = await self._repository.summary_counts(
            self._now() - timedelta(days=7),
        )
        rows = []
        for step in await self._repository.active_steps():
            step_id = str(step["_id"])
            total, completed, in_progress = await self._repository.step_counts(step_id)
            rows.append({
                "step_id": step_id,
                "title": step["title"],
                "order": step["order"],
                "total": total,
                "completed": completed,
                "in_progress": in_progress,
                "completion_rate": round(completed / total * 100 if total else 0, 1),
            })
        result["step_analytics"] = rows
        return result

    async def billing(self) -> dict[str, Any]:
        rows = []
        for partner in await self._repository.billing_partners():
            partner_id = str(partner["_id"])
            customer_id = partner.get("stripe_customer_id")
            invoices = await self._invoices(str(customer_id)) if customer_id else []
            rows.append({
                "partner_id": partner_id,
                "partner_name": partner.get("name", ""),
                "billing_status": partner.get("billing_status", "pending"),
                "usage": await self._usage(partner_id),
                "invoices": invoices,
            })
        return {"partners": rows, "totals": {
            key: sum(int(item["usage"][key]) for item in rows)
            for key in ("pending_users", "pending_amount", "billed_users", "billed_amount")
        }}
