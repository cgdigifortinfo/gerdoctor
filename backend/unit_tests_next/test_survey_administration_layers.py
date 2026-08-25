from __future__ import annotations
import asyncio
from types import SimpleNamespace
import pytest
from slices.survey_administration.models import SurveyDraft
from slices.survey_administration.repository import MongoSurveyAdministrationRepository
from slices.survey_administration.service import (
    DuplicateSurveySlug, SurveyAdministrationService, SurveyNotFound, SurveySlugRequired,
)
from slices.survey_administration.web import SurveyCreate, SurveyUpdate, survey_http_error

def run(value): return asyncio.run(value)
class Repo:
    def __init__(self): self.rows = {}; self.cleared = []; self.updated = None
    async def surveys(self): return sorted(self.rows.values(), key=lambda x:x.get("name", ""))
    async def default_survey(self): return next((x for x in self.rows.values() if x.get("is_default")), None)
    async def survey_by_slug(self, slug, active_only=False):
        return next((x for x in self.rows.values() if x.get("slug") == slug and (not active_only or x.get("is_active"))), None)
    async def survey(self, survey_id): return self.rows.get(survey_id)
    async def duplicate_slug(self, slug, excluding_id=None): return any(k != excluding_id and v.get("slug") == slug for k,v in self.rows.items())
    async def clear_defaults(self, excluding_id=None): self.cleared.append(excluding_id)
    async def insert(self, document): self.rows["new"] = {"_id":"new", **document}; return "new", self.rows["new"]
    async def update(self, survey_id, fields): self.updated=(survey_id,dict(fields)); self.rows[survey_id].update(fields)
def service(repo): return SurveyAdministrationService(repo, lambda:"now", "aerzte")

def test_default_slug_and_user_resolution_paths():
    repo=Repo(); subject=service(repo)
    created=run(subject.ensure_default()); assert created["slug"] == "aerzte"
    assert run(subject.ensure_default()) is created
    assert run(subject.by_slug(None)) is created
    assert run(subject.by_slug("aerzte")) is created
    assert run(subject.for_user({"survey_id":"new"})) is created
    assert run(subject.for_user({})) is created
    assert run(subject.for_user({}, "aerzte")) is created
    with pytest.raises(SurveyNotFound): run(subject.by_slug("missing"))
    repo.rows["new"]["is_default"] = False
    assert run(subject.ensure_default())["slug"] == "aerzte"
    assert run(subject.for_user({"survey_id":"missing"}))["slug"] == "aerzte"

def test_create_list_update_validation_and_default_rules():
    repo=Repo(); subject=service(repo)
    with pytest.raises(SurveySlugRequired): run(subject.create(SurveyDraft("N", " ")))
    repo.rows["old"]={"_id":"old","name":"Old","slug":"used","is_active":True}
    with pytest.raises(DuplicateSurveySlug): run(subject.create(SurveyDraft("N", "used")))
    assert run(subject.create(SurveyDraft("New", " New Slug ", is_default=True))) == "new"
    assert repo.cleared == [None] and [x["name"] for x in run(subject.list_surveys())] == ["New", "Old"]
    with pytest.raises(SurveyNotFound): run(subject.update("missing", {}))
    with pytest.raises(SurveySlugRequired): run(subject.update("new", {"slug":" "}))
    with pytest.raises(DuplicateSurveySlug): run(subject.update("new", {"slug":"used"}))
    assert run(subject.update("new", {"slug":"available"})) == ["slug", "updated_at"]
    fields=run(subject.update("new", {"name":"Updated","is_default":True}))
    assert fields == ["name","is_default","updated_at"] and repo.cleared[-1] == "new"
    fields=run(subject.update("new", {"is_default":False}))
    assert fields[-1] == "updated_at"

class Cursor:
    def __init__(self, rows): self.rows=rows
    def sort(self,*args): return self
    async def to_list(self,n): return self.rows
class Collection:
    def __init__(self, rows=None): self.rows=rows or []; self.calls=[]
    def find(self,*args): self.calls.append(("find",args)); return Cursor(self.rows)
    async def find_one(self,query): self.calls.append(("one",query)); return self.rows[0] if self.rows else None
    async def insert_one(self,doc): self.calls.append(("insert",doc)); return SimpleNamespace(inserted_id="507f1f77bcf86cd799439011")
    async def update_many(self,*args): self.calls.append(("many",args))
    async def update_one(self,*args): self.calls.append(("update",args))

def test_mongo_repository_handles_queries_ids_and_writes():
    rows=[{"_id":"row","name":"N"}]; collection=Collection(rows)
    repo=MongoSurveyAdministrationRepository(SimpleNamespace(surveys=collection)); valid="507f1f77bcf86cd799439011"
    assert run(repo.surveys()) == rows and run(repo.default_survey()) == rows[0]
    assert run(repo.survey_by_slug("s")) == rows[0] and run(repo.survey_by_slug("s",True)) == rows[0]
    assert run(repo.survey("bad")) is None and run(repo.survey(valid)) == rows[0]
    assert run(repo.duplicate_slug("s")) is True and run(repo.duplicate_slug("s",valid)) is True
    run(repo.clear_defaults()); run(repo.clear_defaults(valid))
    assert run(repo.insert({"name":"N"}))[0] == valid
    run(repo.update("bad",{})); run(repo.update(valid,{"name":"U"}))
    assert collection.calls[-1][0] == "update"
    empty=MongoSurveyAdministrationRepository(SimpleNamespace(surveys=Collection()))
    assert run(empty.duplicate_slug("x")) is False

def test_web_models_and_errors():
    assert SurveyCreate(name="N",slug="s").is_active is True and SurveyUpdate().slug is None
    assert survey_http_error(SurveyNotFound()).status_code == 404
    assert survey_http_error(SurveySlugRequired()).detail == "Slug is required"
    assert survey_http_error(DuplicateSurveySlug()).detail == "Survey slug already exists"
    assert survey_http_error(RuntimeError()).status_code == 500
