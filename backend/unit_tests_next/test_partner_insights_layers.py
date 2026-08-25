"""Service, adapter and repository tests for partner insights."""
import asyncio
from datetime import datetime, timezone

from bson import ObjectId

from slices.partner_assignments.models import PartnerWorkStatus
from slices.partner_insights.models import InsightPartner, InsightSnapshot, InsightSubmission
from slices.partner_insights.repository import MongoPartnerInsightsRepository
from slices.partner_insights.service import PartnerInsightsService
from slices.partner_insights.adapters import AssignmentCompletionAdapter, SubmissionCompletionAdapter


def run(awaitable):
    return asyncio.run(awaitable)


class AsyncCursor:
    def __init__(self, rows): self.rows = rows
    def __aiter__(self): self.iterator = iter(self.rows); return self
    async def __anext__(self):
        try: return next(self.iterator)
        except StopIteration: raise StopAsyncIteration
    async def to_list(self, limit): return self.rows


class Collection:
    def __init__(self, rows, one=None): self.rows, self.one = rows, one
    async def find_one(self, query): return self.one
    def find(self, query, projection):
        if query.get("step_order") == 1:
            return AsyncCursor([row for row in self.rows if "data" in row])
        if "step_order" in query:
            return AsyncCursor([row for row in self.rows if row.get("step_order", 0) > 1])
        return AsyncCursor(self.rows)


def test_repository_loads_partner_submissions_acceptance_and_profiles():
    partner_id = str(ObjectId())
    partner = {"_id": ObjectId(partner_id), "name": "P", "registration_status": "active", "is_active": True, "survey_ids": ["s"], "linked_user_ids": ["linked"]}
    class Database: pass
    database = Database()
    database.partners = Collection([], partner)
    database.partner_submissions = Collection([{"user_id": "u", "step_id": "s", "created_at": "now"}])
    database.user_progress = Collection([
        {"user_id": "u", "step_order": 2, "status": "completed"},
        {"user_id": "u", "step_order": 1, "data": {"field_of_study": "Medizin"}},
    ])
    loaded = run(MongoPartnerInsightsRepository(database).load_snapshot(partner_id))
    assert loaded.partner.name == "P"
    assert loaded.accepted_user_ids == frozenset({"u"})
    assert loaded.profiles_by_user["u"].specialty == "Medizin"


def test_repository_skips_progress_queries_without_target_users():
    partner_id = str(ObjectId())
    partner = {"_id": ObjectId(partner_id)}
    class Database: pass
    database = Database()
    database.partners = Collection([], partner)
    database.partner_submissions = Collection([])
    database.user_progress = Collection([])
    loaded = run(MongoPartnerInsightsRepository(database).load_snapshot(partner_id))
    assert loaded.submissions == ()
    assert loaded.accepted_user_ids == frozenset()
    assert loaded.profiles_by_user == {}


class Repository:
    def __init__(self, value): self.value = value
    async def load_snapshot(self, partner_id): return self.value


class SubmissionProvider:
    def __init__(self): self.calls = []
    async def completed(self, submissions): self.calls.append(submissions); return {("u", "s"): True}


class AssignmentProvider:
    def __init__(self): self.calls = []
    async def completed(self, users, partner_id, name): self.calls.append((users, partner_id, name)); return {}


def test_service_skips_providers_while_awaiting_and_composes_active_snapshot():
    clock = lambda: datetime(2026, 8, 24, tzinfo=timezone.utc)
    submissions, assignments = SubmissionProvider(), AssignmentProvider()
    waiting = InsightSnapshot(InsightPartner("p", "P", True), (), frozenset(), {})
    assert run(PartnerInsightsService(Repository(waiting), submissions, assignments, clock).insights("p"))["total_linked_users"] == 0
    assert submissions.calls == []
    active = InsightSnapshot(InsightPartner("p", "P", False, frozenset({"linked"})), (InsightSubmission("u", "s", ""),), frozenset(), {})
    result = run(PartnerInsightsService(Repository(active), submissions, assignments, clock).insights("p"))
    assert result["conversion_funnel"]["completed"] == 1
    assert assignments.calls == [(('linked', 'u'), "p", "P")]


class SubmissionService:
    async def work_statuses(self, documents): return {("u", "s"): {"completed": 1}}


class AssignmentService:
    async def work_statuses(self, users, partner_id, partner_name): return {"u": PartnerWorkStatus(True)}


def test_completion_adapters_translate_existing_service_contracts():
    submissions = (InsightSubmission("u", "s", ""),)
    assert run(SubmissionCompletionAdapter(SubmissionService()).completed(submissions)) == {("u", "s"): True}
    assert run(AssignmentCompletionAdapter(AssignmentService()).completed(("u",), "p", "P")) == {"u": True}
