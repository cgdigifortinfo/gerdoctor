import asyncio
from types import SimpleNamespace

import pytest
from bson import ObjectId

from slices.partner_workspace.command_repository import MongoPartnerWorkspaceCommandRepository
from slices.partner_workspace.command_service import ManagedMilestoneNotFound, PartnerWorkspaceCommandService
from slices.partner_workspace.read_service import PartnerNotLinked
from slices.partner_workspace.command_service import WorkspaceCommandStepNotFound, WorkspaceStepNotManaged
from slices.survey_runtime.progress_service import ProgressCommand


def run(value): return asyncio.run(value)


class Repository:
    def __init__(self, step=True): self.step_value, self.history_rows = ({"_id": "milestone"} if step else None), []
    async def partner(self, _partner_id): return {"name": "Partner"}
    async def step(self, _step_id): return self.step_value
    async def progress(self, _user_id, _step_id): return {"data": {"file": 1}}
    async def history(self, document, *, tolerant=False): self.history_rows.append((dict(document), tolerant))


def service(repository, milestone="milestone"):
    writes = []
    async def status(*_args): return {"milestone_step_id": milestone}
    async def write(**values): writes.append(values)
    return PartnerWorkspaceCommandService(repository, status, write, lambda: "now"), writes


def test_reopen_requires_partner_and_managed_existing_milestone():
    subject, _ = service(Repository())
    with pytest.raises(PartnerNotLinked): run(subject.reopen({}, "user"))
    with pytest.raises(ManagedMilestoneNotFound):
        run(service(Repository(), "")[0].reopen({"partner_id": "p"}, "user"))
    with pytest.raises(ManagedMilestoneNotFound):
        run(service(Repository(step=False))[0].reopen({"partner_id": "p"}, "user"))


def test_reopen_writes_revision_and_tolerant_history():
    repository = Repository(); subject, writes = service(repository)
    step_id = run(subject.reopen({"_id": "actor", "email": "p@example.test", "partner_id": "p"}, "user"))
    assert step_id == "milestone"
    assert writes[0]["status"] == "in_progress"
    assert writes[0]["data"] == {"file": 1}
    assert writes[0]["unset_fields"] == ["completed_at"]
    assert repository.history_rows[0][0]["created_at"] == "now"
    assert repository.history_rows[0][1] is True


class Collection:
    def __init__(self, one=None, count=0, fail=False): self.one, self.count, self.fail, self.calls = one, count, fail, []
    async def find_one(self, *args): self.calls.append(("one", args)); return self.one
    async def update_one(self, *args, **kwargs): self.calls.append(("update", args, kwargs))
    async def insert_one(self, document):
        self.calls.append(("insert", document))
        if self.fail: raise RuntimeError("history unavailable")
    async def count_documents(self, query): self.calls.append(("count", query)); return self.count


def test_mongo_command_repository_maps_ids_updates_history_and_counts():
    valid = str(ObjectId()); collection = Collection({"id": 1})
    history = Collection(fail=True)
    repository = MongoPartnerWorkspaceCommandRepository(SimpleNamespace(
        partners=collection, steps=collection, users=collection, user_progress=collection,
        progress_history=history,
    ))
    assert run(repository.partner("bad")) is None and run(repository.step("bad")) is None and run(repository.user("bad")) is None
    assert run(repository.partner(valid)) == {"id": 1}
    assert run(repository.step(valid)) == {"id": 1}
    assert run(repository.user(valid)) == {"id": 1}
    assert run(repository.progress("u", "s")) == {"id": 1}
    run(repository.update_progress("u", "s", {"$set": {"status": "pending"}}, upsert=False))
    with pytest.raises(RuntimeError): run(repository.history({}, tolerant=False))
    run(repository.history({}, tolerant=True))
    collection.count = 3
    assert run(repository.active_step_count()) == 3


class UpdateRepository(Repository):
    def __init__(self, next_progress=None):
        super().__init__(); self.next_progress = next_progress; self.active_count = 9
    async def progress(self, _user_id, step_id):
        return self.next_progress if step_id == "next" else None
    async def active_step_count(self): return self.active_count


def update_service(*, managed=True, include_step=True, existing=None, next_step=True,
                   next_progress=None, preferences=None):
    repository = UpdateRepository(next_progress); writes=[]; emails=[]; notifications=[]; autos=[]
    current = {"id": "current", "_id": "current", "order": 2, "title": "Current",
               "description": "D", "email_on_leave": True}
    steps = ([current] if include_step else [])
    progress = ([existing] if existing else [])
    target = {"name": "Doctor", "email": "doctor@example.test",
              "notification_preferences": preferences}
    async def status(*_args): return {"milestone_step_id": "milestone"}
    async def write(**values): writes.append(values)
    async def context(*_args): return target, progress, steps, (["current"] if managed else [])
    async def auto(user_id): autos.append(user_id)
    async def notify(*args): notifications.append(args)
    async def email(*args, **kwargs): emails.append((args, kwargs))
    async def visibility(_user_id):
        rows = [{"_id": "hidden", "order": 3, "title": "Hidden"}]
        if next_step: rows.append({"_id": "next", "order": 4, "title": "Next"})
        return rows, [], {"hidden"}, set()
    subject = PartnerWorkspaceCommandService(
        repository, status, write, lambda: "now", context, auto, notify, email, visibility,
    )
    return subject, repository, writes, emails, notifications, autos


def actor(): return {"_id": "partner-user", "email": "partner@example.test", "partner_id": "partner"}


def test_update_progress_validates_partner_managed_membership_and_step():
    subject, *_ = update_service()
    with pytest.raises(PartnerNotLinked):
        run(subject.update_progress({}, "user", ProgressCommand("current", "pending", {})))
    with pytest.raises(WorkspaceStepNotManaged):
        run(update_service(managed=False)[0].update_progress(actor(), "user", ProgressCommand("current", "pending", {})))
    with pytest.raises(WorkspaceCommandStepNotFound):
        run(update_service(include_step=False)[0].update_progress(actor(), "user", ProgressCommand("current", "pending", {})))


def test_update_in_progress_uses_existing_data_and_starts_missing_progress():
    existing = {"step_id": "current", "data": {"old": 1}}
    subject, repository, writes, emails, notifications, autos = update_service(existing=existing)
    run(subject.update_progress(actor(), "user", ProgressCommand("current", "in_progress", {})))
    assert writes[0]["data"] == {"old": 1}
    assert writes[0]["extra_fields"]["started_at"] == "now"
    assert repository.history_rows[0][0]["action"] == "in_progress"
    assert autos == ["user"] and emails == [] and notifications == []


def test_completed_progress_notifies_unlocks_next_step_and_sends_both_emails():
    subject, _, writes, emails, notifications, _ = update_service(preferences={
        "email_on_step_leave": True, "email_on_step_enter": True,
    })
    run(subject.update_progress(actor(), "user", ProgressCommand("current", "completed", {"new": 1})))
    assert writes[0]["data"] == {"new": 1}
    assert writes[0]["extra_fields"]["completed_at"] == "now"
    assert writes[1]["status"] == "in_progress" and writes[1]["change_type"] == "partner_unlocked_next_step"
    assert len(notifications) == 1
    assert [call[0][1] for call in emails] == ["user_step_completed", "user_next_step_unlocked"]


def test_completed_progress_respects_disabled_email_preferences_and_no_next_step():
    subject, _, writes, emails, notifications, _ = update_service(
        next_step=False, preferences={"email_on_step_leave": False, "email_on_step_enter": False},
    )
    run(subject.update_progress(actor(), "user", ProgressCommand("current", "completed", {})))
    assert len(writes) == 1 and emails == [] and notifications == []


def test_completed_progress_does_not_reopen_already_completed_next_step():
    subject, _, writes, *_ = update_service(next_progress={"status": "completed", "data": {}})
    run(subject.update_progress(actor(), "user", ProgressCommand("current", "completed", {})))
    assert len(writes) == 1


def test_completed_progress_reuses_pending_next_data_and_default_preferences():
    subject, _, writes, emails, notifications, _ = update_service(
        next_progress={"status": "pending", "data": {"saved": 1}}, preferences=None,
    )
    run(subject.update_progress(actor(), "user", ProgressCommand("current", "completed", {})))
    assert writes[1]["data"] == {"saved": 1}
    assert len(emails) == 2 and len(notifications) == 1


def test_completed_progress_unlocks_without_sending_disabled_next_email():
    subject, _, writes, emails, notifications, _ = update_service(
        preferences={"email_on_step_leave": False, "email_on_step_enter": False},
    )
    run(subject.update_progress(actor(), "user", ProgressCommand("current", "completed", {})))
    assert len(writes) == 2 and emails == [] and notifications == []
