from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from bson import ObjectId

from slices.partner_administration.repository import MongoPartnerAdministrationRepository
from slices.partner_administration.listing import (
    MongoPartnerAdministrationListingRepository,
    PartnerAdministrationListingService,
)
from slices.partner_administration.service import (
    InvalidPricedStep, PartnerAdministrationService, UnknownPartner, UnknownSurvey, UnknownUser,
)
from pydantic import ValidationError
from slices.partner_administration.web import (
    PartnerCreate, PartnerUpdate, partner_administration_http_error,
)


class Repository:
    def __init__(self) -> None:
        self.partner = {"_id": "p", "name": "Partner", "user_id": "old"}
        self.user = {"_id": "new", "name": "User"}
        self.survey_count = 1
        self.step_count = 1
        self.calls: list[tuple[Any, ...]] = []

    async def insert(self, document): self.calls.append(("insert", document)); return "p"  # type: ignore[no-untyped-def]
    async def find(self, partner_id): self.calls.append(("find", partner_id)); return self.partner  # type: ignore[no-untyped-def]
    async def update(self, partner_id, fields): self.calls.append(("update", partner_id, fields)); return {**self.partner, **fields} if self.partner else None  # type: ignore[no-untyped-def]
    async def valid_survey_count(self, survey_ids): return self.survey_count  # type: ignore[no-untyped-def]
    async def valid_priced_step_count(self, step_ids): return self.step_count  # type: ignore[no-untyped-def]
    async def find_user(self, user_id): return self.user  # type: ignore[no-untyped-def]
    async def users_for_partner(self, partner_id): return [{"_id": "linked"}]  # type: ignore[no-untyped-def]
    async def set_user_role(self, user_id, fields, remove_partner): self.calls.append(("role", user_id, fields, remove_partner))  # type: ignore[no-untyped-def]
    async def set_primary_user(self, partner_id, user_id): self.calls.append(("primary", partner_id, user_id))  # type: ignore[no-untyped-def]
    async def delete(self, partner_id): self.calls.append(("delete", partner_id))  # type: ignore[no-untyped-def]


def test_service_runs_crud_and_user_relationship_use_cases():
    async def scenario() -> None:
        repository = Repository()
        service = PartnerAdministrationService(repository)
        assert await service.create({"name": "P", "description": "D"}, "now") == "p"
        updated = await service.update("p", {"survey_ids": ["s"], "step_user_fee_cents": {"step": 1}}, "now")
        assert updated["survey_ids"] == ["s"]
        deletion = await service.delete("p", "users")
        assert deletion.partner_name == "Partner" and deletion.user_ids == ("linked",)
        assert await service.link_user("p", "new", "users", "partners") == "User"
        await service.unlink_user("p", "users")
        repository.partner = {"_id": "p", "name": "Partner"}
        assert await service.link_user("p", "new", None, None) == "User"
        await service.unlink_user("p", None)
        assert ("primary", "p", None) in repository.calls
    asyncio.run(scenario())


def test_service_reports_every_invalid_reference():
    async def scenario() -> None:
        repository = Repository()
        service = PartnerAdministrationService(repository)
        repository.survey_count = 0
        with pytest.raises(UnknownSurvey): await service.update("p", {"survey_ids": ["s"]}, "now")
        repository.survey_count, repository.step_count = 1, 0
        with pytest.raises(InvalidPricedStep): await service.update("p", {"step_user_fee_cents": {"s": 1}}, "now")
        repository.partner = None
        with pytest.raises(UnknownPartner): await service.update("p", {}, "now")
        with pytest.raises(UnknownPartner): await service.delete("p", None)
        repository.user = None
        with pytest.raises(UnknownUser): await service.link_user("p", "u", None, None)
        repository.user, repository.partner = {"name": "U"}, None
        with pytest.raises(UnknownPartner): await service.link_user("p", "u", None, None)
        with pytest.raises(UnknownPartner): await service.unlink_user("p", None)
    asyncio.run(scenario())


def test_web_error_mapping_is_stable():
    cases = [(UnknownPartner(), 404), (UnknownUser(), 404), (UnknownSurvey(), 400), (InvalidPricedStep(), 400), (ValueError(), 400)]
    assert [partner_administration_http_error(error).status_code for error, _ in cases] == [code for _, code in cases]


def test_partner_request_models_normalize_and_reject_prices():
    assert PartnerCreate(name="P", description="D", contact_email="").contact_email is None
    assert PartnerCreate(name="P", description="D", step_user_fee_cents={"s": 0}).step_user_fee_cents == {"s": 0}
    assert PartnerUpdate(contact_email="").contact_email is None
    assert PartnerUpdate(step_user_fee_cents={"s": 1}).step_user_fee_cents == {"s": 1}
    with pytest.raises(ValidationError):
        PartnerCreate(name="P", description="D", step_user_fee_cents={"s": -1})
    with pytest.raises(ValidationError):
        PartnerUpdate(step_user_fee_cents={"s": -1})


class Cursor:
    def sort(self, *args): return self  # type: ignore[no-untyped-def]
    async def to_list(self, limit: int): return [{"_id": ObjectId()}]  # type: ignore[no-untyped-def]


class Collection:
    def __init__(self) -> None: self.calls = []
    async def insert_one(self, document): self.calls.append(("insert", document)); return SimpleNamespace(inserted_id=ObjectId())  # type: ignore[no-untyped-def]
    async def find_one(self, query): self.calls.append(("find_one", query)); return {"_id": next(iter(query.values()))}  # type: ignore[no-untyped-def]
    async def update_one(self, query, operation): self.calls.append(("update", query, operation))  # type: ignore[no-untyped-def]
    async def count_documents(self, query): self.calls.append(("count", query)); return 1  # type: ignore[no-untyped-def]
    def find(self, *args): self.calls.append(("find", args)); return Cursor()  # type: ignore[no-untyped-def]
    async def delete_many(self, query): self.calls.append(("delete_many", query))  # type: ignore[no-untyped-def]
    async def delete_one(self, query): self.calls.append(("delete_one", query))  # type: ignore[no-untyped-def]


def test_mongo_repository_handles_valid_and_invalid_identifiers():
    async def scenario() -> None:
        database = SimpleNamespace(**{name: Collection() for name in ("partners", "surveys", "steps", "users", "partner_submissions")})
        repository = MongoPartnerAdministrationRepository(database)
        partner_id, user_id = str(ObjectId()), str(ObjectId())
        assert await repository.insert({"name": "P"})
        assert await repository.find(partner_id) is not None and await repository.find("bad") is None
        assert await repository.update(partner_id, {"name": "N"}) is not None and await repository.update("bad", {}) is None
        assert await repository.valid_survey_count([partner_id]) == 1
        assert await repository.valid_priced_step_count([]) == 0
        assert await repository.valid_priced_step_count([partner_id]) == 1
        assert await repository.find_user(user_id) is not None and await repository.find_user("bad") is None
        assert len(await repository.users_for_partner(partner_id)) == 1
        await repository.set_user_role(user_id, {"role": "user"}, True)
        await repository.set_user_role(user_id, {"role": "partner"}, False)
        await repository.set_user_role("bad", {}, False)
        await repository.set_primary_user(partner_id, user_id)
        await repository.set_primary_user(partner_id, None)
        await repository.set_primary_user("bad", None)
        await repository.delete(partner_id)
        await repository.delete("bad")
    asyncio.run(scenario())


def test_partner_administration_listing_builds_sorted_complete_read_model():
    class ListingRepository:
        async def partners(self):
            return [
                {"_id": "b", "name": "Beta", "linked_user_ids": ["linked"],
                 "tags": ["service"], "survey_ids": ["survey"]},
                {"_id": "a", "name": "Alpha", "linked_user_ids": []},
            ]

        async def users(self):
            return [
                {"_id": "linked", "name": "Linked", "email": "l@x.de", "role": "user"},
                {"_id": "dashboard", "name": "Dashboard", "email": "d@x.de",
                 "role": "partner", "partner_id": "b"},
            ]

        async def submissions(self):
            return [{"partner_id": "b", "user_id": "submitted"}, {"user_id": "ignored"}]

        async def service_steps(self):
            return [{"_id": "step", "title": "Service", "filter_tag": "service",
                     "survey_id": "survey", "order": 1}]

    async def statuses(user_ids, partner_id, partner_name):
        return {user_id: {"completed": user_id == "linked"} for user_id in user_ids}

    rows = asyncio.run(PartnerAdministrationListingService(
        ListingRepository(), statuses,
    ).list())
    assert [row["name"] for row in rows] == ["Alpha", "Beta"]
    beta = rows[1]
    assert beta["pending_registrations"] == 1
    assert [user["id"] for user in beta["linked_users"]] == ["dashboard", "linked"]
    assert beta["service_steps"][0]["id"] == "step"


def test_mongo_partner_administration_listing_reads_all_collections():
    async def scenario() -> None:
        database = SimpleNamespace(**{
            name: Collection()
            for name in ("partners", "users", "partner_submissions", "steps")
        })
        repository = MongoPartnerAdministrationListingRepository(database)
        assert await repository.partners()
        assert await repository.users()
        assert await repository.submissions()
        assert await repository.service_steps()
    asyncio.run(scenario())
