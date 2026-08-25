"""Repository and service tests for partner selection."""
from __future__ import annotations

import asyncio

from bson import ObjectId

from slices.partner_selection.models import SelectablePartner, SelectionKind, SelectionStep, SelectionUser
from slices.partner_selection.repository import MongoPartnerSelectionRepository
from slices.partner_selection.service import PartnerSelectionService


def run(awaitable):
    return asyncio.run(awaitable)


class Cursor:
    def __init__(self, rows): self.rows = rows
    async def to_list(self, limit): return self.rows[:limit]


class Collection:
    def __init__(self, rows=(), one=None):
        self.rows, self.one, self.calls = list(rows), one, []
    async def find_one(self, query):
        self.calls.append(("one", query)); return self.one
    def find(self, query):
        self.calls.append(("many", query)); return Cursor(self.rows)
    async def delete_many(self, query): self.calls.append(("delete", query))
    async def update_one(self, query, update): self.calls.append(("update", query, update))
    async def insert_one(self, document): self.calls.append(("insert", document))


class Database: pass


def test_repository_handles_invalid_ids_and_maps_selection_documents() -> None:
    step_id, partner_id = str(ObjectId()), str(ObjectId())
    database = Database()
    database.steps = Collection(one={"_id": ObjectId(step_id), "step_type": "partner_selection"})
    database.partners = Collection(rows=[{"_id": ObjectId(partner_id), "name": "P", "is_active": True}])
    repository = MongoPartnerSelectionRepository(database)
    assert run(repository.find_step("bad")) is None
    assert run(repository.find_step(step_id)).id == step_id
    assert run(repository.find_partners(("bad",))) == ()
    assert run(repository.find_partners((partner_id, "bad")))[0].id == partner_id
    assert database.steps.calls[0][1] == {"_id": ObjectId(step_id), "is_deleted": {"$ne": True}}


def test_repository_handles_missing_or_non_selection_step_and_lists_by_tag() -> None:
    database = Database()
    database.steps = Collection(one=None)
    database.partners = Collection(rows=[])
    repository = MongoPartnerSelectionRepository(database)
    assert run(repository.find_step(str(ObjectId()))) is None
    assert run(repository.list_active_partners("medical")) == ()
    assert database.partners.calls[-1] == ("many", {"is_active": True, "tags": "medical"})
    run(repository.list_active_partners(""))
    assert database.partners.calls[-1] == ("many", {"is_active": True})


def test_repository_persists_selection_submissions() -> None:
    partner_id = str(ObjectId())
    database = Database()
    database.steps = Collection()
    database.partners = Collection(one={"_id": ObjectId(partner_id), "name": "Partner"})
    database.partner_submissions = Collection(one={"_id": "mongo", "id": "public"})
    repository = MongoPartnerSelectionRepository(database)

    assert run(repository.partner_document("bad")) is None
    assert run(repository.partner_document(partner_id))["name"] == "Partner"
    run(repository.remove_other_submissions("user", "step", ("p1", "p2")))
    assert database.partner_submissions.calls[-1] == ("delete", {
        "user_id": "user", "step_id": "step", "partner_id": {"$nin": ["p1", "p2"]},
    })
    assert run(repository.submission("user", "partner", None))["id"] == "public"
    assert database.partner_submissions.calls[-1] == ("one", {
        "user_id": "user", "partner_id": "partner",
    })
    run(repository.submission("user", "partner", "step"))
    assert database.partner_submissions.calls[-1][1]["step_id"] == "step"
    run(repository.update_submission("mongo", {"status": "submitted"}))
    assert database.partner_submissions.calls[-1][0] == "update"
    run(repository.insert_submission({"id": "new"}))
    assert database.partner_submissions.calls[-1] == ("insert", {"id": "new"})


class Repository:
    def __init__(self):
        self.calls = []
        self.step = SelectionStep("step", SelectionKind.SINGLE, "survey", "tag", {})
        self.partners = (SelectablePartner("p", "Partner", frozenset({"tag"}), True, {"id": "p", "name": "Partner"}),)
    async def find_step(self, step_id): self.calls.append(("step", step_id)); return self.step
    async def find_partners(self, partner_ids): self.calls.append(("partners", partner_ids)); return self.partners
    async def list_active_partners(self, tag): self.calls.append(("list", tag)); return self.partners


def test_service_loads_dependencies_once_and_builds_plan() -> None:
    repository = Repository()
    plan = run(PartnerSelectionService(repository).prepare(
        user=SelectionUser("u", "survey"), step_id="step", partner_ids=("p", "p"), data={}, multiple=False,
    ))
    assert plan.partner_ids == ("p",)
    assert repository.calls == [("step", "step"), ("partners", ("p",))]


def test_service_skips_step_lookup_for_legacy_and_sorts_list() -> None:
    repository = Repository()
    plan = run(PartnerSelectionService(repository).prepare(
        user=SelectionUser("u", None), step_id=None, partner_ids=("p",), data=None, multiple=False,
    ))
    assert plan.step is None
    assert repository.calls == [("partners", ("p",))]
    assert run(PartnerSelectionService(repository).list_partners("tag")) == ({"id": "p", "name": "Partner"},)
    assert repository.calls[-1] == ("list", "tag")
