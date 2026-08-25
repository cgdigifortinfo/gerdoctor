from __future__ import annotations

import asyncio

import pytest

from slices.document_workflow.mappers import document_workflow_context
from slices.document_workflow.repository import MongoDocumentWorkflowRepository
from slices.document_workflow.service import DocumentWorkflowReadOnly, DocumentWorkflowService
from slices.document_workflow.web import document_workflow_http_error


class Repository:
    def __init__(self, context):  # type: ignore[no-untyped-def]
        self.context = context

    async def load(self, user_id: str, survey_id: str | None):  # type: ignore[no-untyped-def]
        assert (user_id, survey_id) == ("u", "survey")
        return self.context


class Cursor:
    def __init__(self, rows):  # type: ignore[no-untyped-def]
        self.rows = rows
        self.sort_args = None

    def sort(self, *args):  # type: ignore[no-untyped-def]
        self.sort_args = args
        return self

    async def to_list(self, limit: int):
        assert limit in (200, 500)
        return self.rows


class Collection:
    def __init__(self, rows):  # type: ignore[no-untyped-def]
        self.rows = rows
        self.calls = []

    def find(self, *args):  # type: ignore[no-untyped-def]
        self.calls.append(args)
        return Cursor(self.rows)


class Database:
    def __init__(self) -> None:
        self.steps = Collection([{"_id": "s", "order": 1}])
        self.user_progress = Collection([{"step_id": "s"}])


def test_service_allows_unknown_or_editable_steps() -> None:
    async def scenario() -> None:
        service = DocumentWorkflowService(Repository(document_workflow_context([], [])))
        assert await service.state("u", "survey") == {}
        await service.assert_editable("u", "survey", "unknown")
    asyncio.run(scenario())


def test_service_rejects_locked_step_and_web_maps_conflict() -> None:
    async def scenario() -> None:
        context = document_workflow_context([
            {"id": "d", "order": 1, "step_type": "decision", "conditions": [
                {"action": "read_only", "source_step_order": 2, "operator": "status_is", "value": "completed"}]},
            {"id": "u", "order": 2, "step_type": "form", "fields": [{"field_type": "file"}]},
            {"id": "p", "order": 3, "step_type": "partner_multiselection"},
            {"id": "m", "order": 4, "step_type": "milestone"},
        ], [{"step_id": "u", "status": "completed"}])
        service = DocumentWorkflowService(Repository(context))
        with pytest.raises(DocumentWorkflowReadOnly) as captured:
            await service.assert_editable("u", "survey", "d")
        assert captured.value.args == ("d",)
        error = document_workflow_http_error(captured.value)
        assert (error.status_code, error.detail) == (
            409, "Dieser Schritt ist nach dem Dokumenten-Upload schreibgeschützt.")
    asyncio.run(scenario())


def test_mongo_repository_scopes_active_non_deleted_steps_and_progress() -> None:
    async def scenario() -> None:
        database = Database()
        repository = MongoDocumentWorkflowRepository(database)
        context = await repository.load("u", "survey")
        assert context.steps[0].id == "s" and context.progress[0].step_id == "s"
        assert database.steps.calls == [({"is_active": True, "is_deleted": {"$ne": True}, "survey_id": "survey"},)]
        assert database.user_progress.calls == [({"user_id": "u", "survey_id": "survey"}, {"_id": 0})]
        await repository.load("u", None)
        assert database.steps.calls[-1] == ({"is_active": True, "is_deleted": {"$ne": True}},)
        assert database.user_progress.calls[-1] == ({"user_id": "u"}, {"_id": 0})
    asyncio.run(scenario())
