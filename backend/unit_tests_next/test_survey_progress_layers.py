import asyncio
from types import SimpleNamespace

import pytest
from bson import ObjectId

from slices.survey_runtime.progress_service import (
    ProgressCommand, ProgressStepNotFound, SurveyProgressService,
)
from slices.survey_runtime.progress_repository import MongoSurveyProgressRepository


def run(value): return asyncio.run(value)


class Repository:
    def __init__(self, step=None, existing=None):
        self.step_value, self.existing, self.history_rows = step, existing, []
    async def step(self, _step_id): return self.step_value
    async def progress(self, _user_id, _step_id): return self.existing
    async def step_count(self, _survey_id): return 7
    async def history(self, document): self.history_rows.append(dict(document))


def service(repository):
    calls = SimpleNamespace(edit=[], write=[], email=[], auto=[])
    async def editable(*args): calls.edit.append(args)
    async def default(): return {"_id": "default"}
    async def write(**kwargs): calls.write.append(kwargs)
    async def email(*args, **kwargs): calls.email.append((args, kwargs))
    async def auto(*args): calls.auto.append(args)
    subject = SurveyProgressService(repository, editable, default, write, email, auto,
                                    lambda: "now", frozenset({"content"}))
    return subject, calls


def user(**values):
    return {"_id": "user", "name": "Doctor", "email": "doctor@example.test",
            "role": "user", **values}


def step(**values):
    return {"_id": ObjectId(), "title": "Step", "order": 1, "fields": [], **values}


def test_service_rejects_unknown_step():
    subject, _ = service(Repository())
    with pytest.raises(ProgressStepNotFound):
        run(subject.update(user(), ProgressCommand("missing", "pending", {})))


def test_new_completed_progress_uses_default_survey_and_only_completes_current_step():
    repository = Repository(step(
        email_on_enter=True, email_on_leave=True,
        email_subject_enter="Enter", email_body_enter="Body",
        email_subject_leave="Leave", email_body_leave="Done",
    ))
    subject, calls = service(repository)
    run(subject.update(user(notification_preferences={
        "email_on_step_enter": True, "email_on_step_leave": True,
    }), ProgressCommand("step", "completed", {"anerkennungsstatus": "planned"})))
    assert calls.edit == [("user", repository.step_value)]
    assert [row[0][1] for row in calls.email] == ["user_step_entered", "user_step_completed"]
    assert calls.write[0]["extra_fields"] == {
        "survey_id": "default", "started_at": "now", "completed_at": "now",
    }
    assert calls.auto == [("user",)]
    assert repository.history_rows[0]["timestamp"] == "now"


def test_existing_progress_sends_edit_and_preserves_started_time():
    repository = Repository(step(
        survey_id="survey", order=2, email_on_edit=True,
        email_subject_edit=None, email_body_edit=None,
    ), {"started_at": "before"})
    subject, calls = service(repository)
    run(subject.update(user(notification_preferences={"email_on_step_edit": True}),
                       ProgressCommand("step", "in_progress", {"answer": 1})))
    assert [row[0][1] for row in calls.email] == ["user_step_updated"]
    assert calls.email[0][1] == {"override_subject": "", "override_body": ""}
    assert calls.write[0]["extra_fields"] == {"survey_id": "survey"}


def test_pending_or_skipped_progress_suppresses_optional_notifications_and_validation():
    repository = Repository(step(
        survey_id="survey", email_on_enter=True, email_on_leave=True, email_on_edit=True,
        required_fields=["required"],
    ))
    subject, calls = service(repository)
    run(subject.update(user(survey_id="user-survey", notification_preferences={
        "email_on_step_enter": False, "email_on_step_leave": False,
    }), ProgressCommand("step", "completed", {"skipped": True})))
    assert calls.email == []
    assert calls.write[0]["extra_fields"]["survey_id"] == "survey"


class Collection:
    def __init__(self, one=None, count=0): self.one, self.count, self.calls = one, count, []
    async def find_one(self, query): self.calls.append(("one", query)); return self.one
    async def count_documents(self, query): self.calls.append(("count", query)); return self.count
    async def insert_one(self, document): self.calls.append(("insert", document))


def test_mongo_progress_repository_maps_all_operations():
    step_collection = Collection({"_id": "step"}, 4)
    progress = Collection({"status": "pending"})
    history = Collection()
    repository = MongoSurveyProgressRepository(SimpleNamespace(
        steps=step_collection, user_progress=progress, progress_history=history,
    ))
    assert run(repository.step("bad")) is None
    valid = str(ObjectId())
    assert run(repository.step(valid)) == {"_id": "step"}
    assert run(repository.progress("user", valid))["status"] == "pending"
    assert run(repository.step_count("survey")) == 4
    run(repository.history({"action": "completed"}))
    assert history.calls == [("insert", {"action": "completed"})]
