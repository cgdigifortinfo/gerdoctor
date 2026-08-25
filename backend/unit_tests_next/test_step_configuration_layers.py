from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from slices.step_configuration.migration import migrate_database_step_configurations
from slices.step_configuration.repository import MongoStepConfigurationRepository
from slices.step_configuration.service import StepConfigurationNotFound, StepConfigurationService
from slices.step_configuration.web import step_configuration_http_error
from slices.step_configuration.administration import (
    MongoStepAdministrationRepository,
    StepAdministrationInvalidId,
    StepAdministrationNotFound,
    StepAdministrationService,
)
from slices.step_configuration.web_models import StepCondition, StepCreate, StepResponse
from pydantic import ValidationError


class Repository:
    def __init__(self) -> None:
        self.created = None
        self.updated = None
        self.fail = False

    async def create(self, values, actor):  # type: ignore[no-untyped-def]
        self.created = (values, actor)
        return "step"

    async def update(self, step_id, values, unset_fields, actor, change_type):  # type: ignore[no-untyped-def]
        if self.fail:
            raise KeyError(step_id)
        self.updated = (step_id, values, unset_fields, actor, change_type)
        return 1, 2

    async def find(self, step_id: str, include_deleted: bool = False):  # type: ignore[no-untyped-def]
        return None


def test_service_orchestrates_create_update_and_missing_translation() -> None:
    async def scenario() -> None:
        repository = Repository()
        service = StepConfigurationService(repository, lambda: datetime(2024, 1, 1, tzinfo=timezone.utc))
        assert await service.create({"title": "A"}, "survey", {"id": "admin"}) == "step"
        assert repository.created[0]["created_at"] == "2024-01-01T00:00:00+00:00"
        assert await service.update("step", {"title": "B"}, frozenset({"title"}), {"id": "admin"}) == (1, 2)
        assert repository.updated[-1] == "update"
        repository.fail = True
        with pytest.raises(StepConfigurationNotFound) as captured:
            await service.update("missing", {}, frozenset(), {})
        error = step_configuration_http_error(captured.value)
        assert (captured.value.args, error.status_code, error.detail) == (("missing",), 404, "Step not found")
    asyncio.run(scenario())


class AdministrationRepository:
    def __init__(self) -> None:
        self.rows = {
            "507f1f77bcf86cd799439011": {"_id": "507f1f77bcf86cd799439011", "title": "A", "order": 2, "survey_id": "s"},
            "507f1f77bcf86cd799439012": {"_id": "507f1f77bcf86cd799439012", "title": "B", "order": 2, "survey_id": "other"},
        }
        self.updates = []

    async def steps(self, survey_id, include_deleted): return list(self.rows.values())  # type: ignore[no-untyped-def]
    async def find(self, step_id, include_deleted=True): return self.rows.get(step_id)  # type: ignore[no-untyped-def]
    async def versions(self, step): return [{"version": 1}]  # type: ignore[no-untyped-def]
    async def versioned_update(self, step, fields, actor, change_type):  # type: ignore[no-untyped-def]
        self.updates.append((step, fields, actor, change_type))
        return 1, 2


def test_step_administration_service_covers_all_operations() -> None:
    async def scenario() -> None:
        repository = AdministrationRepository()
        service = StepAdministrationService(repository, lambda: datetime(2024, 1, 2, tzinfo=timezone.utc))
        assert len(await service.steps(None, False)) == 2
        with pytest.raises(StepAdministrationInvalidId): await service.versions("bad")
        with pytest.raises(StepAdministrationNotFound): await service.versions("507f1f77bcf86cd799439099")
        assert await service.versions("507f1f77bcf86cd799439011") == [{"version": 1}]
        changes = await service.reorder([
            "507f1f77bcf86cd799439011", "507f1f77bcf86cd799439012", "missing",
        ], "s", {"id": "admin"})
        assert changes == [{"step_id": "507f1f77bcf86cd799439011", "before_version": 1, "after_version": 2}]
        await service.reorder([
            "507f1f77bcf86cd799439011", "507f1f77bcf86cd799439012",
        ], None, {})
        repository.rows["507f1f77bcf86cd799439011"]["flow_position"] = {"x": 1.0, "y": 2.0}
        layout = await service.save_layout({
            "507f1f77bcf86cd799439011": {"x": 1.0, "y": 2.0},
            "507f1f77bcf86cd799439012": {"x": 3.0, "y": 4.0},
            "missing": {"x": 0.0, "y": 0.0},
        }, {})
        assert layout[0]["step_id"] == "507f1f77bcf86cd799439012"
        with pytest.raises(StepAdministrationNotFound): await service.archive("missing", {})
        step, before, after = await service.archive("507f1f77bcf86cd799439011", {"id": "a"})
        assert step["title"] == "A" and (before, after) == (1, 2)
        assert repository.updates[-1][1]["deleted_at"] == "2024-01-02T00:00:00+00:00"
        repository.rows["507f1f77bcf86cd799439011"]["is_deleted"] = True
        assert (await service.archive("507f1f77bcf86cd799439011", {}))[1:] == (None, None)
    asyncio.run(scenario())


def test_step_administration_mongo_repository_covers_queries_and_adapters() -> None:
    async def scenario() -> None:
        calls = []
        valid = "507f1f77bcf86cd799439011"

        class Cursor:
            def __init__(self, rows): self.rows = rows
            def sort(self, *args): calls.append(("sort", args)); return self
            async def to_list(self, limit): return self.rows

        class Collection:
            def __init__(self, rows): self.rows = rows
            def find(self, *args): calls.append(("find", args)); return Cursor(self.rows)
            async def find_one(self, query): calls.append(("find_one", query)); return self.rows[0] if self.rows else None

        database = type("DB", (), {
            "steps": Collection([{"_id": valid, "title": "A"}]),
            "step_versions": Collection([{"version": 1}]),
        })()

        async def ensure(db, step): calls.append(("ensure", step))
        async def update(db, step, fields, unset, actor, change_type):
            calls.append(("update", fields, change_type)); return 2, 3, step

        repository = MongoStepAdministrationRepository(database, ensure, update)
        assert await repository.steps(None, False)
        assert await repository.steps("survey", True)
        assert await repository.find("bad") is None
        assert await repository.find(valid, True)
        assert await repository.find(valid, False)
        assert await repository.versions({"_id": valid}) == [{"version": 1}]
        assert await repository.versioned_update({"_id": valid}, {"order": 2}, {}, "reorder") == (2, 3)
    asyncio.run(scenario())


def test_step_web_models_validate_compound_conditions_and_defaults() -> None:
    base = {"title": "A", "description": "D", "order": 1, "step_type": "form"}
    assert StepCreate(**base).duration_unit == "days"
    assert StepResponse(id="s", **base).current_version == 1
    assert StepCondition(all_of=[{"field": "x"}]).all_of
    assert StepCondition(any_of=[{"field": "x"}]).any_of
    with pytest.raises(ValidationError): StepCondition(all_of=[], any_of=[{"field": "x"}])
    with pytest.raises(ValidationError): StepCondition(all_of=[])
    with pytest.raises(ValidationError): StepCondition(any_of=[])


class AsyncCursor:
    def __init__(self, rows):  # type: ignore[no-untyped-def]
        self._rows = iter(rows)

    def __aiter__(self):  # type: ignore[no-untyped-def]
        return self

    async def __anext__(self):  # type: ignore[no-untyped-def]
        try:
            return next(self._rows)
        except StopIteration as error:
            raise StopAsyncIteration from error


class Steps:
    def __init__(self) -> None:
        self.updates = []

    def find(self, query):  # type: ignore[no-untyped-def]
        assert query == {}
        return AsyncCursor([
            {"_id": 1, "fields": [{"name": "ok", "field_type": "text", "id": "ok", "label": "ok", "required": False, "width": "full", "help_text": ""}], "form_schema_version": 1},
            {"_id": 2, "fields": [{"label": "Legacy"}]},
        ])

    async def update_one(self, query, update):  # type: ignore[no-untyped-def]
        self.updates.append((query, update))


class Database:
    def __init__(self) -> None:
        self.steps = Steps()


def test_infrastructure_migration_updates_only_noncanonical_steps() -> None:
    async def scenario() -> None:
        database = Database()
        assert await migrate_database_step_configurations(database) == 1
        assert database.steps.updates[0][0] == {"_id": 2}
        assert database.steps.updates[0][1]["$set"]["form_schema_version"] == 1
    asyncio.run(scenario())


def test_mongo_repository_delegates_versioned_create_find_and_update(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def scenario() -> None:
        calls = []

        class Result:
            inserted_id = "created"

        class MongoSteps:
            async def insert_one(self, values):  # type: ignore[no-untyped-def]
                calls.append(("insert", values))
                return Result()

            async def find_one(self, query):  # type: ignore[no-untyped-def]
                calls.append(("find", query))
                return {"_id": query["_id"], "title": "Step"}

        class MongoDatabase:
            steps = MongoSteps()

        async def insert_version(database, step, version, actor, change_type):  # type: ignore[no-untyped-def]
            calls.append(("version", step, version, actor, change_type))

        async def update_versioned(database, step, values, unset, actor, change_type):  # type: ignore[no-untyped-def]
            calls.append(("update", step, values, unset, actor, change_type))
            return 2, 3, step

        repository = MongoStepConfigurationRepository(MongoDatabase(), insert_version, update_versioned)
        assert await repository.create({"title": "A"}, {"id": "admin"}) == "created"
        valid_id = "507f1f77bcf86cd799439011"
        assert await repository.find("bad") is None
        found = await repository.find(valid_id)
        assert found is not None and found["title"] == "Step"
        await repository.find(valid_id, include_deleted=True)
        assert calls[-1][1] == {"_id": calls[-1][1]["_id"]}
        assert await repository.update(valid_id, {"title": "B"}, ("price",), {}, "edit") == (2, 3)

        async def missing(query):  # type: ignore[no-untyped-def]
            return None
        MongoDatabase.steps.find_one = missing
        with pytest.raises(KeyError):
            await repository.update(valid_id, {}, (), {}, "edit")
    asyncio.run(scenario())
