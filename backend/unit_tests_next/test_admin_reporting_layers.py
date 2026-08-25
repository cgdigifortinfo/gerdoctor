from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from slices.admin_reporting.repository import MongoAdminReportingRepository
from slices.admin_reporting.service import AdminReportingService


def run(value): return asyncio.run(value)  # type: ignore[no-untyped-def]


class Repository:
    async def summary_counts(self, recent_since):
        self.since = recent_since
        return {"total_users": 2}

    async def active_steps(self):
        return [
            {"_id": "empty", "title": "Empty", "order": 1},
            {"_id": "used", "title": "Used", "order": 2},
        ]

    async def step_counts(self, step_id):
        return (0, 0, 0) if step_id == "empty" else (4, 3, 1)

    async def billing_partners(self):
        return [
            {"_id": "a", "name": "A", "stripe_customer_id": "cus", "billing_status": "active"},
            {"_id": "b", "name": "B"},
        ]


def test_admin_reporting_service_builds_analytics_and_billing_totals():
    repository = Repository()

    async def invoices(customer_id): return [{"id": customer_id}]
    async def usage(partner_id):
        multiplier = 1 if partner_id == "a" else 2
        return {key: multiplier for key in (
            "pending_users", "pending_amount", "billed_users", "billed_amount",
        )}

    service = AdminReportingService(
        repository, invoices, usage, lambda: datetime(2026, 8, 25, tzinfo=timezone.utc),
    )
    analytics = run(service.analytics())
    assert repository.since.isoformat() == "2026-08-18T00:00:00+00:00"
    assert analytics["step_analytics"][0]["completion_rate"] == 0
    assert analytics["step_analytics"][1]["completion_rate"] == 75.0
    billing = run(service.billing())
    assert billing["partners"][0]["invoices"] == [{"id": "cus"}]
    assert billing["partners"][1]["invoices"] == []
    assert billing["totals"]["pending_users"] == 3


class Cursor:
    def __init__(self, rows): self.rows = rows
    def sort(self, *args): return self
    async def to_list(self, limit): return self.rows


class Collection:
    def __init__(self, rows=(), count=1): self.rows = list(rows); self.count = count; self.calls = []
    async def count_documents(self, query): self.calls.append(query); return self.count
    def find(self, *args): self.calls.append(args); return Cursor(self.rows)


def test_mongo_admin_reporting_repository_executes_every_read_query():
    users = Collection(count=2)
    partners = Collection(({"_id": "p"},), count=3)
    submissions = Collection(count=4)
    steps = Collection(({"_id": "s"},))
    progress = Collection(count=5)
    database = type("DB", (), {
        "users": users, "partners": partners, "partner_submissions": submissions,
        "steps": steps, "user_progress": progress,
    })()
    repository = MongoAdminReportingRepository(database)
    counts = run(repository.summary_counts(datetime(2026, 1, 1, tzinfo=timezone.utc)))
    assert counts == {
        "total_users": 2, "total_partners": 3, "total_submissions": 4,
        "admin_count": 2, "partner_count": 2, "recent_registrations": 2,
    }
    assert run(repository.active_steps()) == [{"_id": "s"}]
    assert run(repository.step_counts("s")) == (5, 5, 5)
    assert run(repository.billing_partners()) == [{"_id": "p"}]
