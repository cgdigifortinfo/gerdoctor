"""Repository and service contract tests for partner assignments."""
import asyncio

from bson import ObjectId

from slices.partner_assignments.models import AssignmentContext, FlowStep, StepKind, StepProgress
from slices.partner_assignments.repository import MongoPartnerAssignmentRepository
from slices.partner_assignments.service import PartnerAssignmentService


def run(awaitable):
    return asyncio.run(awaitable)


class Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.sort_args = None

    def sort(self, value):
        self.sort_args = value
        return self

    async def to_list(self, limit):
        return self.rows


class Collection:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def find(self, query, projection):
        self.calls.append((query, projection))
        return Cursor(self.rows)


class Database:
    def __init__(self, user_id):
        self.users = Collection([{"_id": ObjectId(user_id), "survey_id": "survey"}])
        self.steps = Collection([
            {"_id": ObjectId(), "survey_id": "survey", "order": 1, "step_type": "partner_selection"},
        ])
        self.user_progress = Collection([
            {"user_id": user_id, "step_id": "choice", "data": {"selected_partner_id": "p"}},
        ])


def test_repository_maps_and_groups_bulk_context():
    user_id = str(ObjectId())
    database = Database(user_id)
    context = run(MongoPartnerAssignmentRepository(database).load_context((user_id, "invalid")))
    assert len(context.steps_by_user[user_id]) == 1
    assert context.steps_by_user["invalid"] == ()
    assert context.progress_by_user[user_id][0].selected_partner_ids == frozenset({"p"})
    assert context.progress_by_user["invalid"] == ()


class Repository:
    def __init__(self, context):
        self.context = context
        self.calls = []

    async def load_context(self, user_ids):
        self.calls.append(user_ids)
        return self.context


def test_service_deduplicates_users_and_returns_typed_statuses():
    steps = (
        FlowStep("choice", 1, StepKind.PARTNER_SELECTION),
        FlowStep("milestone", 2, StepKind.MILESTONE),
    )
    progress = (
        StepProgress("choice", selected_partner_ids=frozenset({"p"})),
        StepProgress("milestone", "completed", completed_at="now"),
    )
    repository = Repository(AssignmentContext({"u": steps}, {"u": progress}))
    service = PartnerAssignmentService(repository)
    assert run(service.work_statuses([], "p", "")) == {}
    statuses = run(service.work_statuses(["", "u", "u"], "p", ""))
    assert repository.calls == [("u",)]
    assert statuses["u"].completed
