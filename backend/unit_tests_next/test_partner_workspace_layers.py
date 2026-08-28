"""Repository and service tests for the partner user workspace."""
from __future__ import annotations

import asyncio

import pytest
from bson import ObjectId

from slices.partner_workspace.models import WorkspaceProgress, WorkspaceStep, WorkspaceUser
from slices.partner_workspace.repository import MongoPartnerWorkspaceRepository
from slices.partner_workspace.service import PartnerWorkspaceService, WorkspaceUserNotFound
from slices.partner_workspace.profile import (
    MongoPartnerProfileRepository,
    PartnerProfileNotLinked,
    PartnerProfileService,
)
from slices.partner_workspace.web import PartnerSelfUpdate


def run(awaitable):
    return asyncio.run(awaitable)


class Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.sort_args = None

    def sort(self, *args):
        self.sort_args = args
        return self

    async def to_list(self, limit):
        return self.rows[:limit]


class Collection:
    def __init__(self, rows=(), one=None):
        self.rows = list(rows)
        self.one = one
        self.find_calls = []

    async def find_one(self, query, projection):
        self.find_calls.append((query, projection))
        return self.one

    def find(self, query, projection=None):
        self.find_calls.append((query, projection))
        return Cursor(self.rows)


class Database:
    pass


def test_repository_rejects_invalid_id_and_maps_survey_scoped_workspace() -> None:
    user_id = str(ObjectId())
    database = Database()
    database.users = Collection(one={"_id": ObjectId(user_id), "name": "User", "survey_id": "survey"})
    database.user_progress = Collection([{"step_id": "selection", "survey_id": "survey", "data": {"selected_partner_id": "partner"}}])
    database.steps = Collection([{"_id": ObjectId(), "survey_id": "survey", "order": 1, "step_type": "partner_selection"}])
    repository = MongoPartnerWorkspaceRepository(database)

    assert run(repository.find_user("invalid")) is None
    assert run(repository.find_user(user_id)).name == "User"
    progress = run(repository.load_progress(user_id, "survey"))
    steps = run(repository.load_steps("survey"))
    assert progress[0].step_id == "selection"
    assert steps[0].step_type == "partner_selection"
    assert database.user_progress.find_calls[0][0] == {"user_id": user_id, "survey_id": "survey"}
    assert database.steps.find_calls[0][0] == {"is_active": True, "is_deleted": {"$ne": True}, "survey_id": "survey"}


def test_repository_supports_legacy_users_without_survey_and_missing_user() -> None:
    database = Database()
    database.users = Collection(one=None)
    database.user_progress = Collection()
    database.steps = Collection()
    repository = MongoPartnerWorkspaceRepository(database)
    assert run(repository.find_user(str(ObjectId()))) is None
    assert run(repository.load_progress("u", None)) == ()
    assert run(repository.load_steps(None)) == ()
    assert database.user_progress.find_calls[0][0] == {"user_id": "u"}
    assert database.steps.find_calls[0][0] == {"is_active": True, "is_deleted": {"$ne": True}}


class Repository:
    def __init__(self, user):
        self.user = user
        self.calls = []
        self.steps = (
            WorkspaceStep("selection", 1, "Choose", "partner_selection", "", "", {}),
            WorkspaceStep("milestone", 2, "Documents", "milestone", "", "", {}),
        )
        self.progress = (
            WorkspaceProgress("selection", "completed", 1, {"selected_partner_id": "partner"}, {"step_id": "selection", "data": {"selected_partner_id": "partner"}}),
        )

    async def find_user(self, user_id):
        self.calls.append(("user", user_id))
        return self.user

    async def load_progress(self, user_id, survey_id):
        self.calls.append(("progress", user_id, survey_id))
        return self.progress

    async def load_steps(self, survey_id):
        self.calls.append(("steps", survey_id))
        return self.steps


def test_service_loads_one_consistent_workspace_and_resolves_managed_steps() -> None:
    repository = Repository(WorkspaceUser("u", "User", "u@example.com", "survey", {}))
    workspace = run(PartnerWorkspaceService(repository).load("u", "partner", "Partner"))
    assert workspace.user.id == "u"
    assert workspace.managed_step_ids == ("selection", "milestone")
    assert repository.calls == [("user", "u"), ("progress", "u", "survey"), ("steps", "survey")]


def test_service_stops_when_user_does_not_exist() -> None:
    repository = Repository(None)
    with pytest.raises(WorkspaceUserNotFound):
        run(PartnerWorkspaceService(repository).load("missing", "partner", "Partner"))
    assert repository.calls == [("user", "missing")]


class ProfileRepository:
    def __init__(self): self.row = None; self.updated = None
    async def partner(self, partner_id): return self.row
    async def update_partner(self, partner_id, fields): self.updated = (partner_id, dict(fields))


def test_partner_profile_service_handles_unlinked_missing_complete_and_updates() -> None:
    repository = ProfileRepository()
    service = PartnerProfileService(repository)
    base = {"name": "User", "email": "u@x.de"}
    assert run(service.profile(base))["partner_id"] is None
    missing = run(service.profile({**base, "partner_id": "p"}))
    assert missing == {**base, "partner_name": None, "partner_id": "p"}
    repository.row = {"_id": "p", "name": "Partner"}
    profile = run(service.profile({**base, "partner_id": "p"}))
    assert profile["partner_name"] == "Partner" and profile["is_active"] is True
    with pytest.raises(PartnerProfileNotLinked):
        run(service.update_organization(base, {}, "now"))
    partner_id, fields = run(service.update_organization(
        {**base, "partner_id": "p"},
        {"description": "D", "tags": [" b ", "a", "", 1], "ignored": None}, "now",
    ))
    assert partner_id == "p" and fields == ["description", "tags", "updated_at"]
    assert repository.updated[1]["tags"] == ["a", "b"]
    run(service.update_organization({**base, "partner_id": "p"}, {"description": "Only"}, "later"))
    assert PartnerSelfUpdate(tags=["x"]).tags == ["x"]
    with pytest.raises(PartnerProfileNotLinked):
        run(service.update_logo(base, "logo.png", "image/png", b"image", "now"))
    partner_id, logo_url = run(service.update_logo(
        {**base, "partner_id": "p"}, "logo.png", "image/png",
        b"\x89PNG\r\n\x1a\nbody", "now",
    ))
    assert partner_id == "p" and logo_url.startswith("data:image/png;base64,")
    assert repository.updated[1] == {"logo_url": logo_url, "updated_at": "now"}


def test_mongo_partner_profile_repository_validates_and_updates() -> None:
    from types import SimpleNamespace
    from bson import ObjectId

    class Partners:
        def __init__(self): self.calls = []
        async def find_one(self, query): self.calls.append(("find", query)); return {"_id": query["_id"]}
        async def update_one(self, *args): self.calls.append(("update", args))

    partners = Partners()
    repository = MongoPartnerProfileRepository(SimpleNamespace(partners=partners))
    assert run(repository.partner("bad")) is None
    valid = str(ObjectId())
    assert str(run(repository.partner(valid))["_id"]) == valid
    run(repository.update_partner("bad", {}))
    run(repository.update_partner(valid, {"description": "D"}))
    assert partners.calls[-1][0] == "update"
