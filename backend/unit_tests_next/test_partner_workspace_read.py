import asyncio
from types import SimpleNamespace

import pytest
from bson import ObjectId

from slices.partner_workspace.read_repository import MongoPartnerWorkspaceReadRepository
from slices.partner_workspace.read_service import PartnerNotLinked, PartnerWorkspaceReadService


def run(value): return asyncio.run(value)


class Repository:
    def __init__(self):
        self.partner_value = {"name": "Partner", "linked_user_ids": ["linked", "missing"]}
        self.submission_rows = [
            {"user_id": "submitted", "user_email": "s@example.test", "step_id": "choice"},
            {"status": "legacy", "user_email": ""},
        ]
        self.user_rows = [
            {"_id": "linked", "name": "Linked", "email": "l@example.test"},
            {"_id": "other", "name": "Other", "email": "o@example.test", "created_at": "then"},
        ]
    async def partner(self, _partner_id): return self.partner_value
    async def submissions(self, _partner_id): return [dict(row) for row in self.submission_rows]
    async def step_one_data(self, _ids): return {
        "submitted": {"fachrichtung_gewuenscht": "Cardiology", "anerkennungsverfahren_bundesland": "Berlin"},
        "linked": {"fachrichtung_praktiziert": "Surgery"},
        "other": {"field_of_study": "Neurology"},
    }
    async def users(self, user_ids=None):
        return [row for row in self.user_rows if user_ids is None or str(row["_id"]) in user_ids]
    async def submitted_user_ids(self, _partner_id): return {"submitted"}


def service(repository):
    async def metrics(ids): return {uid: {"completion_pct": 25, "estimated_completion": "date"} for uid in ids}
    async def work(ids, *_args): return {uid: {
        "completed": False, "completed_at": None, "milestone_step_id": "milestone",
    } for uid in ids}
    async def submission_work(_rows): return {("submitted", "choice"): {
        "completed": True, "completed_at": "done", "milestone_step_id": "m",
        "service_step_id": "service", "service_step_title": "Service", "milestone_step_title": "Milestone",
    }}
    async def email(_actor, _partner, value): return f"visible:{value}"
    return PartnerWorkspaceReadService(repository, metrics, work, submission_work, email)


def test_read_service_requires_partner_link():
    subject = service(Repository())
    with pytest.raises(PartnerNotLinked): run(subject.submissions({}))
    with pytest.raises(PartnerNotLinked): run(subject.other_users({}))


def test_submission_read_model_keeps_each_service_and_adds_linked_users():
    result = run(service(Repository()).submissions({"partner_id": "partner"}))
    submitted = result[0]
    assert submitted["user_email"] == "visible:s@example.test"
    assert submitted["partner_work_completed"] is True
    assert submitted["service_step_id"] == "service"
    assert submitted["field_of_study"] == "Cardiology"
    assert result[1]["status"] == "legacy"
    linked = next(row for row in result if row.get("user_id") == "linked")
    assert linked["status"] == "linked"
    assert linked["field_of_study"] == "Surgery"
    assert all(row.get("user_id") != "missing" for row in result)


def test_other_users_excludes_linked_and_submitted_users():
    result = run(service(Repository()).other_users({"partner_id": "partner"}))
    assert result == [{
        "user_id": "other", "user_name": "Other", "user_email": "visible:o@example.test",
        "completion_pct": 25, "estimated_completion": "date", "field_of_study": "Neurology",
        "bundesland": "", "created_at": "then",
    }]


class AsyncCursor:
    def __init__(self, rows): self.rows = list(rows); self.index = 0
    def __aiter__(self): self.index = 0; return self
    async def __anext__(self):
        if self.index >= len(self.rows): raise StopAsyncIteration
        value = self.rows[self.index]; self.index += 1; return value
    async def to_list(self, _length): return list(self.rows)


class Collection:
    def __init__(self, rows=(), one=None): self.rows, self.one, self.calls = list(rows), one, []
    async def find_one(self, query): self.calls.append(("one", query)); return self.one
    def find(self, *args): self.calls.append(("find", args)); return AsyncCursor(self.rows)


def test_mongo_read_repository_handles_ids_queries_and_empty_sets():
    partner_id = str(ObjectId())
    database = SimpleNamespace(
        partners=Collection(one={"name": "P"}),
        partner_submissions=Collection([{"user_id": "u"}]),
        user_progress=Collection([{"user_id": "u", "data": {"x": 1}}]),
        users=Collection([{"_id": ObjectId(), "name": "U"}]),
    )
    repository = MongoPartnerWorkspaceReadRepository(database)
    assert run(repository.partner("bad")) is None
    assert run(repository.partner(partner_id)) == {"name": "P"}
    assert run(repository.submissions(partner_id)) == [{"user_id": "u"}]
    assert run(repository.step_one_data(set())) == {}
    assert run(repository.step_one_data({"u"})) == {"u": {"x": 1}}
    assert len(run(repository.users({str(ObjectId()), "bad"}))) == 1
    assert len(run(repository.users())) == 1
    assert run(repository.submitted_user_ids(partner_id)) == {"u"}
