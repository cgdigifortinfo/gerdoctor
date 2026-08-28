"""Coverage-complete contracts for legacy authentication and Mongo adapters."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from pydantic import ValidationError
from bson import ObjectId
from fastapi import HTTPException

from slices.groups_permissions import permissions
from slices.identity_access import auth
from slices.identity_access.repository import InvalidUserIdentifier
from slices.identity_access.service import IdentityNotFound, InvalidAccessToken
from slices.step_versioning import facade
from slices.step_versioning.repository import MongoStepVersioningRepository
from slices.survey_runtime import repository as runtime_repository
from slices.step_configuration import form_builder
from models import StepCondition


class Cursor:
    def __init__(self, rows=()): self.rows = list(rows)
    def __aiter__(self):
        async def values():
            for row in self.rows: yield row
        return values()
    def sort(self, *_args): return self
    async def to_list(self, _limit): return self.rows


class Collection:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.find_one = AsyncMock(return_value=None)
        self.update_one = AsyncMock()
        self.update_many = AsyncMock()
        self.insert_one = AsyncMock()
    def find(self, *_args, **_kwargs): return Cursor(self.rows)


@pytest.mark.anyio
async def test_permission_storage_resolution_and_role_migration(monkeypatch) -> None:
    group_id, wrong_id, default_id = ObjectId(), ObjectId(), ObjectId()
    groups = Collection([{"_id": group_id, "permissions": ["users.view"], "role": "user"}])
    groups.find_one.side_effect = [
        {"_id": group_id, "name": "G", "role": "user"}, None,
        {"_id": default_id}, {"_id": default_id},
    ]
    users = Collection()
    monkeypatch.setattr(permissions, "db", SimpleNamespace(permission_groups=groups, users=users))
    assert permissions.normalize_permissions(["users.view"]) == ["users.view"]
    assert "users.view" in await permissions.effective_permissions({"group_ids": [str(group_id), "invalid"], "permission_overrides": {}})
    assert "portal.user.access" in await permissions.effective_permissions({"role": "user"})
    assert await permissions.has_permission({"email": "admin@example.com"}, "anything")
    summaries = await permissions.permission_group_summaries({"group_ids": [str(group_id), "invalid"]})
    assert summaries == [{"id": str(group_id), "name": "G", "role": "user"}]
    assert await permissions.default_group_id("unknown") is None

    groups.rows = [{"_id": group_id, "role": "user"}]
    monkeypatch.setattr(permissions, "default_group_id", AsyncMock(return_value=str(default_id)))
    user = {"_id": ObjectId(), "role": "user", "group_ids": [str(group_id), str(wrong_id), "bad"]}
    normalized = await permissions.ensure_user_role_group(user)
    assert normalized["group_ids"] == [str(group_id)]
    unchanged = await permissions.ensure_user_role_group({**normalized})
    assert unchanged == normalized
    assert permissions.permission_for_admin_request("GET", "/api/admin/users")
    assert permissions.permission_for_portal_request("GET", "/api/partner/profile")
    groups.rows = []
    assert await permissions.effective_permissions({"group_ids": ["invalid"], "permission_overrides": {}}) == []
    assert await permissions.effective_permissions({"permission_overrides": {}}) == []
    user_without_valid_groups = {"_id": ObjectId(), "role": "user", "group_ids": ["invalid"]}
    assert (await permissions.ensure_user_role_group(user_without_valid_groups))["group_ids"] == [str(default_id)]


@pytest.mark.anyio
async def test_permission_group_seeding_create_upgrade_and_users(monkeypatch) -> None:
    existing = [
        {"_id": ObjectId(), "key": "administrators", "permissions": ["*"], "default_permission_version": 1},
        {"_id": ObjectId(), "key": "survey_users", "permissions": [], "default_permission_version": 1},
        {"_id": ObjectId(), "key": "partners", "permissions": [], "default_permission_version": 1},
    ]
    groups = Collection()
    groups.find_one.side_effect = existing + [
        {"_id": ObjectId()}, {"_id": ObjectId()}, {"_id": ObjectId()},
    ]
    users = Collection([{"_id": ObjectId(), "role": "user"}])
    monkeypatch.setattr(permissions, "db", SimpleNamespace(permission_groups=groups, users=users))
    monkeypatch.setattr(permissions, "ensure_user_role_group", AsyncMock())
    assert await permissions.ensure_permission_groups() == 0
    assert groups.update_one.await_count == 1
    assert users.update_one.await_count == 1
    assert users.update_many.await_count == 1

    groups.find_one.side_effect = [None, None, None, None, None, None]
    assert await permissions.ensure_permission_groups() == 3
    assert groups.insert_one.await_count == 3
    current_version = [
        {"_id": ObjectId(), "key": definition["key"], "permissions": definition["permissions"],
         "default_permission_version": 0}
        for definition in permissions.DEFAULT_GROUPS
    ]
    groups.find_one.side_effect = current_version + [None, None, None]
    await permissions.ensure_permission_groups()


@pytest.mark.anyio
async def test_auth_tokens_current_user_errors_and_guards(monkeypatch) -> None:
    codec = SimpleNamespace(
        access_token=MagicMock(return_value="access"), refresh_token=MagicMock(return_value="refresh"),
        decode=MagicMock(return_value={"sub": "u"}),
    )
    monkeypatch.setenv("JWT_SECRET", "secret")
    monkeypatch.setattr(auth, "_token_codec", lambda: codec)
    assert auth.get_jwt_secret() == "secret"
    assert auth.create_access_token("u", "e", "user") == "access"
    assert auth.create_refresh_token("u") == "refresh"
    service = MagicMock(); service.current_user = AsyncMock(return_value={"role": "admin"})
    monkeypatch.setattr(auth, "IdentityAccessService", lambda _repo: service)
    monkeypatch.setattr(auth, "access_token_from_request", lambda _request: "token")
    assert (await auth.get_current_user(MagicMock()))["role"] == "admin"

    for error, detail in [
        (InvalidAccessToken(), "Invalid token type"), (IdentityNotFound(), "User not found"),
        (jwt.ExpiredSignatureError(), "Token expired"), (jwt.InvalidTokenError(), "Invalid token"),
        (InvalidUserIdentifier("bad"), "Invalid token"), (KeyError("x"), "Invalid token"),
        (TypeError("x"), "Invalid token"),
    ]:
        codec.decode.side_effect = error
        with pytest.raises(HTTPException, match=detail): await auth.get_current_user(MagicMock())
    codec.decode.side_effect = None
    monkeypatch.setattr(auth, "get_current_user", AsyncMock(return_value={"role": "admin"}))
    assert (await auth.require_role("admin")(MagicMock()))["role"] == "admin"
    with pytest.raises(HTTPException): await auth.require_role("user")(MagicMock())
    monkeypatch.setattr(permissions, "has_permission", AsyncMock(return_value=True))
    assert await auth.require_permission("x", "admin")(MagicMock())
    with pytest.raises(HTTPException): await auth.require_permission("x", "user")(MagicMock())
    monkeypatch.setattr(permissions, "has_permission", AsyncMock(return_value=False))
    with pytest.raises(HTTPException): await auth.require_permission("x")(MagicMock())


@pytest.mark.anyio
async def test_step_versioning_facade_delegates_every_operation(monkeypatch) -> None:
    assert facade._service(SimpleNamespace())
    service = SimpleNamespace(**{
        name: AsyncMock(return_value=name) for name in (
            "insert_step_version", "ensure_step_version", "update_step_versioned",
            "bind_revision_documents", "write_progress_revision", "migrate", "revision_view",
        )
    })
    monkeypatch.setattr(facade, "_service", lambda _db: service)
    assert facade.utc_now()
    assert await facade.insert_step_version(None, {}, 1, None, "x") == "insert_step_version"
    assert await facade.ensure_step_version(None, {}) == "ensure_step_version"
    assert await facade.update_step_versioned(None, {}, {}, None, {}, "x") == "update_step_versioned"
    assert await facade.bind_revision_documents(None, {}) == "bind_revision_documents"
    assert await facade.write_progress_revision(None, user_id="u") == "write_progress_revision"
    assert await facade.migrate_step_answer_versioning(None) == "migrate"
    assert await facade.revision_view(None, "u") == "revision_view"


def _versioning_db() -> SimpleNamespace:
    names = ("step_versions", "steps", "document_bindings", "files", "user_progress",
             "user_progress_revisions")
    return SimpleNamespace(**{name: Collection() for name in names})


@pytest.mark.anyio
async def test_step_versioning_repository_all_persistence_paths(monkeypatch) -> None:
    database = _versioning_db(); clock = SimpleNamespace(now_iso=lambda: "now")
    repo = MongoStepVersioningRepository(database, clock)
    step_id = ObjectId(); step = {"_id": step_id, "title": "T"}
    document = await repo.insert_step_version(step, 1, None, "create")
    assert document["version"] == 1
    database.steps.find_one.return_value = None
    with pytest.raises(ValueError): await repo.ensure_step_version({"id": str(step_id)})
    database.steps.find_one.return_value = step
    assert await repo.ensure_step_version({"id": str(step_id)}) == 1
    assert await repo.ensure_step_version({**step, "current_version": 2}) == 2
    database.steps.find_one.return_value = {**step, "current_version": 2, "updated": True}
    before, after, updated = await repo.update_step_versioned(
        {**step, "current_version": 2}, {"title": "N"}, ["old"], {}, "update")
    assert (before, after, updated["updated"]) == (2, 3, True)

    revision = {"data": {"files": [{"file_id": "f"}]}, "user_id": "u", "step_id": str(step_id),
                "step_version": 1, "revision": 1, "created_at": "now"}
    assert await repo.bind_revision_documents(revision) == 1
    monkeypatch.setattr(repo, "ensure_step_version", AsyncMock(return_value=1))
    monkeypatch.setattr(repo, "bind_revision_documents", AsyncMock(return_value=1))
    database.user_progress.find_one.return_value = {"revision": 1}
    result = await repo.write_progress_revision(
        user_id="u", step=step, status="completed", data={}, actor=None,
        change_type="save", extra_fields={"x": 1}, unset_fields=["old"])
    assert result["revision"] == 2
    database.steps.find_one.return_value = {**step, "current_version": 2}
    await repo.update_step_versioned({**step, "current_version": 2}, {"title": "N"}, None, {}, "update")
    database.user_progress.find_one.return_value = None
    await repo.write_progress_revision(
        user_id="u", step=step, status="pending", data={}, actor=None,
        change_type="save", unset_fields=None,
    )

    database.steps.rows = [step]
    database.user_progress.rows = [{"_id": ObjectId(), "user_id": "u", "step_id": str(step_id),
                                    "status": "completed", "updated_at": "then"}]
    database.steps.find_one.return_value = {**step, "current_version": 1}
    stats = await repo.migrate()
    assert stats == {"steps": 1, "answers": 1, "documents": 1}

    database.user_progress_revisions.rows = [{"user_id": "u", "step_id": str(step_id), "step_version": 1, "revision": 1}]
    database.steps.rows = [{**step, "current_version": 1}]
    database.step_versions.rows = [{"step_id": str(step_id), "version": 1, "snapshot": {}}]
    assert len(await repo.revision_view("u")) == 1


@pytest.mark.anyio
async def test_survey_runtime_repository_single_bulk_and_empty(monkeypatch) -> None:
    user_id, survey_id = str(ObjectId()), "survey"
    database = SimpleNamespace(users=Collection(), steps=Collection(), user_progress=Collection())
    repo = runtime_repository.MongoSurveyRuntimeRepository(database)
    mapper = MagicMock(side_effect=lambda steps, progress: (steps, progress))
    monkeypatch.setattr(runtime_repository, "runtime_context_from_documents", mapper)
    database.users.find_one.return_value = {"survey_id": survey_id}
    database.steps.rows = [{"survey_id": survey_id, "order": 1}]
    database.user_progress.rows = [{"user_id": user_id}]
    assert (await repo.load(user_id))[0]
    database.users.find_one.return_value = None
    assert await repo.load("invalid")
    assert await repo.load_many(()) == {}
    database.users.rows = [{"_id": ObjectId(user_id), "survey_id": survey_id}]
    result = await repo.load_many((user_id, user_id, ""))
    assert user_id in result
    database.users.rows = []
    assert user_id in await repo.load_many((user_id,))


def test_step_condition_rejects_empty_and_conflicting_compounds() -> None:
    for values in ({"all_of": [], "any_of": [{}]}, {"all_of": []}, {"any_of": []}):
        with pytest.raises(ValidationError): StepCondition(**values)


@pytest.mark.anyio
async def test_form_builder_database_migration_facade(monkeypatch) -> None:
    migration = AsyncMock(return_value=3)
    monkeypatch.setattr(form_builder, "migrate_database_step_configurations", migration)
    assert await form_builder.migrate_database_form_configs(SimpleNamespace()) == 3
