from __future__ import annotations

import asyncio
from types import SimpleNamespace
import pytest
from pydantic import ValidationError

from slices.cms_public_settings.repository import MongoCmsPublicSettingsRepository
from slices.cms_public_settings.service import CmsPublicSettingsService
from slices.cms_public_settings.web import CMSContentUpdate, SiteSettingsUpdate


def run(value): return asyncio.run(value)


class Repo:
    def __init__(self):
        self.cms = {}
        self.site = {}
        self.saved = []
        self.inserted = None
    async def cms_sections(self): return list(self.cms.values())
    async def cms_section(self, section): return self.cms.get(section)
    async def save_cms_section(self, section, fields):
        self.saved.append((section, dict(fields))); self.cms[section] = {**self.cms.get(section, {}), **fields}
    async def settings(self): return dict(self.site)
    async def update_settings(self, fields): self.site.update(fields)
    async def insert_settings(self, fields): self.inserted = dict(fields); self.site.update(fields)


def service(repo): return CmsPublicSettingsService(repo, lambda: "now", frozenset({"secret"}))


def test_service_reads_updates_and_filters_content_and_settings():
    repo = Repo(); subject = service(repo)
    assert run(subject.content("missing")) == {"content": {}, "translations": {}}
    repo.cms["home"] = {"section": "home", "content": {"title": "T"}}
    assert run(subject.all_content()) == {"home": {"content": {"title": "T"}, "translations": {}}}
    assert run(subject.content("home"))["content"] == {"title": "T"}
    run(subject.update_content("home", {"title": "N"}, None, False))
    assert repo.saved[-1][1]["updated_at"] == "now"
    repo.site = {"secret": "s", "stripe_test_publishable_key": "pk", "site_title": "Title"}
    assert run(subject.admin_settings({"ready": True}))["secret"] == "••••••••"
    public = run(subject.public_settings({"ready": True}))
    assert public == {"site_title": "Title", "stripe": {"ready": True}}
    assert run(subject.update_settings({"site_title": "New", "secret": "••••••••", "x": None})) == ["site_title"]
    assert run(subject.update_settings({"x": None})) == []


def test_service_seeds_new_backfills_existing_and_creates_settings_once():
    repo = Repo(); repo.cms["old"] = {"section": "old", "content": {"a": 1}}
    subject = service(repo)
    run(subject.seed({"new": {"x": 1}, "plain": {"p": 1}, "old": {"a": 1, "b": 2}},
                     {"new": {"x": "one"}}, {"site_title": "IHCA"}))
    assert repo.cms["new"]["translations"] == {"en": {"x": "one"}}
    assert "translations" not in repo.cms["plain"]
    assert repo.cms["old"]["content"] == {"a": 1, "b": 2}
    assert repo.inserted == {"site_title": "IHCA", "created_at": "now"}
    saved = len(repo.saved)
    run(subject.seed({"new": {"x": 1}, "plain": {"p": 1}, "old": {"a": 1, "b": 2}},
                     {"new": {"x": "one"}}, {"site_title": "ignored"}))
    assert len(repo.saved) == saved


class Cursor:
    async def to_list(self, limit): return [{"section": "home"}]
class Collection:
    def __init__(self, found=None): self.found = found; self.calls = []
    def find(self, query, projection): self.calls.append(("find", query, projection)); return Cursor()
    async def find_one(self, query, projection): self.calls.append(("one", query, projection)); return self.found
    async def update_one(self, query, update, upsert=False): self.calls.append(("update", query, update, upsert))
    async def insert_one(self, document): self.calls.append(("insert", document))


def test_mongo_repository_maps_all_collections_and_empty_settings():
    cms, site = Collection({"section": "home"}), Collection(None)
    repo = MongoCmsPublicSettingsRepository(SimpleNamespace(cms_content=cms, site_settings=site))
    assert run(repo.cms_sections()) == [{"section": "home"}]
    assert run(repo.cms_section("home")) == {"section": "home"}
    run(repo.save_cms_section("home", {"content": {}}))
    assert run(repo.settings()) == {}
    run(repo.update_settings({"title": "T"})); run(repo.insert_settings({"title": "T"}))
    assert cms.calls[-1][-1] is True
    assert site.calls[-1] == ("insert", {"_key": "global", "title": "T"})
    site.found = {"title": "T"}
    assert run(repo.settings()) == {"title": "T"}


def test_web_models_are_typed_and_validate_non_negative_fee():
    assert CMSContentUpdate(content={"x": 1}).translations is None
    assert SiteSettingsUpdate(site_title="IHCA").site_title == "IHCA"
    with pytest.raises(ValidationError): SiteSettingsUpdate(stripe_partner_user_fee_cents=-1)
