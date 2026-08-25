from __future__ import annotations
import asyncio
from types import SimpleNamespace
import pytest
from slices.step_templates.models import AppliedTemplate, TemplateDraft
from slices.step_templates.repository import MongoStepTemplateRepository
from slices.step_templates.service import SourceStepNotFound, StepTemplateService, TemplateNotFound
from slices.step_templates.web import StepTemplateCreate, StepTemplateUpdate, step_template_http_error

def run(value): return asyncio.run(value)

class Repo:
    def __init__(self): self.tpl = {}; self.steps = {}; self.users = []; self.updated = None; self.deleted = None
    async def templates(self): return list(self.tpl.values())
    async def template(self, template_id): return self.tpl.get(template_id)
    async def insert_template(self, document): self.tpl["new"] = {"_id": "new", **document}; return "new"
    async def update_template(self, template_id, fields): self.updated = (template_id, dict(fields))
    async def delete_template(self, template_id): self.deleted = template_id
    async def step(self, step_id): return self.steps.get(step_id)
    async def shifted_steps(self, survey_id, order): return [s for s in self.steps.values() if s["order"] >= order]
    async def insert_step(self, document): return "created", {"_id": "created", **document}
    async def survey_user_ids(self, survey_id): return list(self.users)

def make_service(repo):
    calls = {"shift": [], "version": [], "progress": []}
    async def shift(step, fields, unset, actor, change): calls["shift"].append((step, fields, unset, actor, change))
    async def version(step, number, actor, change): calls["version"].append((step, number, actor, change))
    async def progress(user, step, status, data, actor, change): calls["progress"].append((user, step, status, data, actor, change))
    return StepTemplateService(repo, lambda: "now", shift, version, progress), calls

def test_service_crud_and_missing_paths():
    repo = Repo(); subject, _ = make_service(repo)
    assert run(subject.templates()) == []
    assert run(subject.create(TemplateDraft("N", "D", {"order": 1, "x": 2}))) == "new"
    assert run(subject.templates())[0]["config"] == {"x": 2}
    fields = run(subject.update("new", {"name": "Updated", "config": None}))
    assert fields == ["name", "updated_at"] and repo.updated[0] == "new"
    assert run(subject.delete("new")) == "N" and repo.deleted == "new"
    with pytest.raises(TemplateNotFound): run(subject.delete("missing"))
    with pytest.raises(SourceStepNotFound): run(subject.create_from_step("missing", "N", "D"))
    repo.steps["source"] = {"_id": "source", "order": 2, "title": "T"}
    assert run(subject.create_from_step("source", "From", "Step")) == "new"
    assert repo.tpl["new"]["config"] == {"title": "T"}

def test_service_apply_versions_shifts_new_step_and_each_users_progress():
    repo = Repo(); repo.tpl["tpl"] = {"_id": "tpl", "config": {"title": "T", "order": 99}}
    repo.steps["later"] = {"_id": "later", "order": 4}; repo.users = ["u1", "u2"]
    subject, calls = make_service(repo)
    result = run(subject.apply("tpl", "survey", 3, {"_id": "admin", "email": "admin@x.de"}))
    assert result == AppliedTemplate("created", "survey")
    assert calls["shift"][0][1] == {"order": 5}
    assert calls["version"][0][1:] == (1, {"id": "admin", "email": "admin@x.de", "role": "admin"}, "template_create")
    assert [item[0] for item in calls["progress"]] == ["u1", "u2"]
    with pytest.raises(TemplateNotFound): run(subject.apply("missing", "survey", 1, {"_id": "a", "email": "e"}))

class Cursor:
    def __init__(self, rows): self.rows = rows
    def sort(self, *args): return self
    async def to_list(self, limit): return self.rows
class Collection:
    def __init__(self, rows=None): self.rows = rows or []; self.calls = []
    def find(self, *args): self.calls.append(("find", args)); return Cursor(self.rows)
    async def find_one(self, query, *args): self.calls.append(("one", query)); return self.rows[0] if self.rows else None
    async def insert_one(self, doc): self.calls.append(("insert", doc)); return SimpleNamespace(inserted_id="507f1f77bcf86cd799439011")
    async def update_one(self, *args): self.calls.append(("update", args))
    async def delete_one(self, *args): self.calls.append(("delete", args))

def test_mongo_repository_maps_queries_and_invalid_ids():
    tpl = Collection([{"_id": "t"}]); steps = Collection([{"_id": "s", "order": 2}]); users = Collection([{"_id": "u"}])
    repo = MongoStepTemplateRepository(SimpleNamespace(step_templates=tpl, steps=steps, users=users))
    assert run(repo.templates()) == [{"_id": "t"}]
    assert run(repo.template("bad")) is None and run(repo.step("bad")) is None
    valid = "507f1f77bcf86cd799439011"
    assert run(repo.template(valid)) == {"_id": "t"} and run(repo.step(valid))["order"] == 2
    assert run(repo.insert_template({"x": 1})) == valid
    run(repo.update_template("bad", {})); run(repo.delete_template("bad"))
    run(repo.update_template(valid, {"x": 2})); run(repo.delete_template(valid))
    assert run(repo.shifted_steps("survey", 2))[0]["order"] == 2
    assert run(repo.insert_step({"title": "T"}))[0] == valid
    assert run(repo.survey_user_ids("survey")) == ["u"]

def test_web_models_and_error_mapping():
    assert StepTemplateCreate(name="N", config={}).description == ""
    assert StepTemplateUpdate().config is None
    assert step_template_http_error(TemplateNotFound()).detail == "Template not found"
    assert step_template_http_error(SourceStepNotFound()).detail == "Step not found"
    assert step_template_http_error(RuntimeError()).status_code == 500
