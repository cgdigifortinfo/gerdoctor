"""Repository and service contract tests for partner submissions."""
import asyncio

from bson import ObjectId

from slices.partner_submissions.models import SubmissionContext
from slices.partner_submissions.repository import MongoPartnerSubmissionRepository
from slices.partner_submissions.service import PartnerSubmissionService


def run(awaitable):
    return asyncio.run(awaitable)


class Cursor:
    def __init__(self, rows):
        self.rows = rows

    def sort(self, value):
        return self

    async def to_list(self, limit):
        return self.rows


class Collection:
    def __init__(self, rows):
        self.rows = rows

    def find(self, query, projection):
        return Cursor(self.rows)


class Database:
    def __init__(self, user_id):
        self.users = Collection([{"_id": ObjectId(user_id), "survey_id": "survey"}])
        self.steps = Collection([
            {"_id": "service", "survey_id": "survey", "order": 1, "title": "Service", "step_type": "form"},
            {"_id": "milestone", "survey_id": "survey", "order": 2, "title": "Done", "step_type": "milestone"},
        ])
        self.user_progress = Collection([
            {"user_id": user_id, "step_id": "milestone", "status": "completed", "completed_at": "now"},
        ])


def test_repository_loads_grouped_typed_context():
    user_id = str(ObjectId())
    context = run(MongoPartnerSubmissionRepository(Database(user_id)).load_context((user_id, "invalid")))
    assert context.survey_by_user == {user_id: "survey"}
    assert [row.id for row in context.steps_by_survey["survey"]] == ["service", "milestone"]
    assert context.progress_by_user[user_id]["milestone"].completed_at == "now"


class Repository:
    def __init__(self, context):
        self.context = context
        self.calls = []

    async def load_context(self, user_ids):
        self.calls.append(user_ids)
        return self.context


def test_service_deduplicates_users_and_serializes_statuses():
    empty_repository = Repository(SubmissionContext({}, {}, {}))
    assert run(PartnerSubmissionService(empty_repository).work_statuses([])) == {}
    assert empty_repository.calls == []

    user_id = "u"
    repository = Repository(SubmissionContext({user_id: "survey"}, {"survey": ()}, {}))
    statuses = run(PartnerSubmissionService(repository).work_statuses([
        {"user_id": user_id, "step_id": "one"},
        {"user_id": user_id, "step_id": "two"},
    ]))
    assert repository.calls == [(user_id,)]
    assert set(statuses) == {(user_id, "one"), (user_id, "two")}
    assert statuses[(user_id, "one")]["completed"] is False
