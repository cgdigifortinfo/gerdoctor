import asyncio

from slices.audit_trail.models import AuditEntry, AuditPage
from slices.audit_trail.repository import MongoAuditTrailRepository
from slices.audit_trail.service import AuditTrailService


def run(coroutine): return asyncio.run(coroutine)


class Repo:
    def __init__(self): self.entry = None; self.args = None; self.initialized = False
    async def append(self, entry): self.entry = entry
    async def page(self, query, limit, skip): self.args = (query, limit, skip); return AuditPage(({"action": "x"},), 1, ("x",))
    async def ensure_indexes(self): self.initialized = True


def test_service_records_pages_and_initializes_repository():
    repository = Repo(); service = AuditTrailService(repository, lambda: "now")
    run(service.record("actor", "a@b.de", "update", "step", "s", {"x": 1}))
    assert repository.entry == AuditEntry("actor", "a@b.de", "update", "step", "s", {"x": 1}, "now")
    page = run(service.page(0, -1, "update", "a", "z"))
    assert page.to_document() == {"logs": [{"action": "x"}], "total": 1, "action_types": ["x"]}
    assert repository.args == ({"action": "update", "timestamp": {"$gte": "a", "$lte": "z"}}, 0, 0)
    run(service.initialize())
    assert repository.initialized is True


class Cursor:
    def __init__(self, rows): self.rows = rows
    def sort(self, *args): return self
    def skip(self, value): self.rows = self.rows[value:]; return self
    def limit(self, value): self.rows = self.rows[:value]; return self
    async def to_list(self, value): return self.rows[:value]


class Collection:
    def __init__(self): self.rows = [{"action": "b"}, {"action": "a"}]; self.inserted = None; self.index = None
    async def insert_one(self, document): self.inserted = document
    async def count_documents(self, query): return len(self.rows)
    def find(self, *args): return Cursor(list(self.rows))
    async def distinct(self, field): return ["b", "a"]
    async def create_index(self, index): self.index = index


class Database:
    def __init__(self): self.audit_logs = Collection()


def test_mongo_repository_appends_pages_with_and_without_limit_and_indexes():
    database = Database(); repository = MongoAuditTrailRepository(database)
    entry = AuditEntry("a", "e", "x", "t", "i", {}, "now")
    run(repository.append(entry))
    assert database.audit_logs.inserted == entry.to_document()
    limited = run(repository.page({}, 1, 0))
    assert limited.total == 2 and len(limited.logs) == 1 and limited.action_types == ("b", "a")
    unlimited = run(repository.page({}, 0, 1))
    assert len(unlimited.logs) == 1
    run(repository.ensure_indexes())
    assert database.audit_logs.index == [("timestamp", -1)]
