from __future__ import annotations

import asyncio
from types import SimpleNamespace

from slices.document_workflow.models import WorkflowStepState
from slices.document_workflow.service import DocumentWorkflowService
from slices.survey_runtime.dashboard import (
    MongoSurveyDashboardRepository,
    SurveyDashboardService,
    all_step_data,
    serialized_step,
)


def run(value): return asyncio.run(value)  # type: ignore[no-untyped-def]


class Repository:
    def __init__(self):
        self.step_rows = [
            {"_id": "s", "title": "Step", "order": 1, "step_type": "form"},
            {"_id": "old", "title": "Old", "order": 2, "step_type": "form"},
        ]
        self.progress_rows = [
            {"step_id": "s", "status": "completed", "data": {"x": 1}},
            {"step_id": "deleted", "status": "completed", "data": {}},
        ]

    async def steps(self, survey_id): return self.step_rows
    async def progress(self, user_id, survey_id): return self.progress_rows
    async def history(self, user_id): return [{"action": "completed"}]
    async def bootstrap(self, user_id, survey_id):
        return self.step_rows, self.progress_rows, [{"action": "completed"}], {"site": "IHCA"}


def test_dashboard_serializers_and_service_read_models(monkeypatch):
    repository = Repository()
    service = SurveyDashboardService(
        repository, lambda steps, progress: {"estimated_completion": "soon"},
    )
    assert serialized_step(repository.step_rows[0]) == {
        "title": "Step", "order": 1, "step_type": "form", "id": "s",
    }
    assert all_step_data(repository.step_rows, repository.progress_rows)[0]["status"] == "completed"
    assert all_step_data(repository.step_rows, [])[0]["status"] == "pending"
    assert run(service.steps("survey"))[0]["id"] == "s"
    assert run(service.progress("u", "survey")) == repository.progress_rows
    assert run(service.all_data("u", "survey"))[0]["data"] == {"x": 1}
    assert run(service.history("u")) == [{"action": "completed"}]
    monkeypatch.setattr(DocumentWorkflowService, "resolve", staticmethod(
        lambda context: {"s": WorkflowStepState(read_only=True)},
    ))
    bootstrap = run(service.bootstrap({"_id": "u"}, "survey"))
    assert bootstrap["steps"][0]["read_only"] is True
    assert "read_only" not in bootstrap["steps"][1]
    assert [row["step_id"] for row in bootstrap["progress"]] == ["s"]
    assert bootstrap["estimated_completion"] == "soon"
    assert bootstrap["notification_preferences"]["email_on_step_enter"] is True
    custom = run(service.bootstrap({"_id": "u", "notification_preferences": {"custom": True}}, "survey"))
    assert custom["notification_preferences"] == {"custom": True}


class Cursor:
    def __init__(self, rows): self.rows = rows
    def sort(self, *args): return self
    async def to_list(self, limit): return self.rows


class Collection:
    def __init__(self, rows=(), row=None): self.rows = list(rows); self.row = row; self.calls = []
    def find(self, *args): self.calls.append(("find", args)); return Cursor(self.rows)
    async def find_one(self, *args): self.calls.append(("find_one", args)); return self.row


def test_mongo_survey_dashboard_repository_reads_individual_and_bootstrap_views():
    steps = Collection(({"_id": "s"},))
    progress = Collection(({"step_id": "s"},))
    history = Collection(({"action": "done"},))
    settings = Collection(row={"site": "IHCA"})
    repository = MongoSurveyDashboardRepository(SimpleNamespace(
        steps=steps, user_progress=progress, progress_history=history,
        site_settings=settings,
    ))
    assert run(repository.steps("survey")) == [{"_id": "s"}]
    assert run(repository.progress("u", "survey")) == [{"step_id": "s"}]
    assert run(repository.history("u")) == [{"action": "done"}]
    loaded = run(repository.bootstrap("u", "survey"))
    assert loaded[-1] == {"site": "IHCA"}
    settings.row = None
    assert run(repository.bootstrap("u", "survey"))[-1] == {}
