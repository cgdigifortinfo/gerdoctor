from __future__ import annotations

import uuid
import asyncio
from datetime import timezone
from typing import get_args

from bson import ObjectId

from infrastructure.clock import SystemUtcClock, system_utc_clock
from infrastructure.identifiers import Uuid4Generator, uuid4_generator
from infrastructure.mongo_ids import object_id_or_none
from infrastructure.mongo_ids import valid_object_ids
from infrastructure.mongo_serialization import mongo_json_safe
from infrastructure.mongo_bootstrap import initialize_mongo_schema
from shared.types import JsonObject, JsonScalar, JsonValue


def test_system_clock_returns_aware_utc_datetime_and_matching_iso_format() -> None:
    clock = SystemUtcClock()
    now = clock.now()
    assert now.tzinfo is timezone.utc
    parsed = clock.now_iso()
    assert parsed.endswith("+00:00")
    assert system_utc_clock.now().tzinfo is timezone.utc


def test_uuid_generator_returns_distinct_valid_version_four_identifiers() -> None:
    generator = Uuid4Generator()
    first, second = generator.new(), generator.new()
    assert first != second
    assert uuid.UUID(first).version == 4
    assert uuid.UUID(second).version == 4
    assert uuid.UUID(uuid4_generator.new()).version == 4


def test_mongo_identifier_conversion_is_total_and_safe() -> None:
    object_id = ObjectId()
    assert object_id_or_none(object_id) == object_id
    assert object_id_or_none(str(object_id)) == object_id
    assert object_id_or_none("invalid") is None
    assert object_id_or_none(None) is None
    assert object_id_or_none(0) is None
    assert valid_object_ids(("invalid", object_id, str(object_id))) == (object_id, object_id)


def test_mongo_json_serialization_removes_internal_ids_and_handles_nested_sequences() -> None:
    object_id = ObjectId()
    assert mongo_json_safe({
        "_id": ObjectId(), "owner": object_id,
        "rows": ({"value": object_id}, ["plain"]),
    }) == {"owner": str(object_id), "rows": [{"value": str(object_id)}, ["plain"]]}
    assert mongo_json_safe("plain") == "plain"


def test_shared_json_types_remain_small_serialization_only_aliases() -> None:
    assert set(get_args(JsonScalar)) == {str, int, float, bool, type(None)}
    assert JsonObject == dict[str, JsonValue]


class IndexCollection:
    def __init__(self, indexes=None):
        self.indexes = indexes or {}; self.created = []; self.dropped = []; self.updated = []
    async def update_many(self, *args): self.updated.append(args)
    async def index_information(self): return self.indexes
    async def drop_index(self, name): self.dropped.append(name)
    async def create_index(self, keys, **options): self.created.append((keys, options))


class Database:
    def __init__(self, indexes=None):
        names = ("users", "surveys", "password_reset_tokens", "login_attempts",
                 "permission_groups", "steps", "user_progress", "partner_submissions",
                 "partner_usage_charges", "files", "partners", "progress_history",
                 "step_versions", "user_progress_revisions", "document_bindings")
        for name in names: setattr(self, name, IndexCollection(indexes if name == "partner_usage_charges" else None))


def test_mongo_bootstrap_creates_schema_and_removes_legacy_usage_index() -> None:
    database = Database({"legacy": {"key": [("partner_id", 1), ("user_id", 1)]}})
    asyncio.run(initialize_mongo_schema(database))
    assert database.users.updated
    assert database.partner_usage_charges.dropped == ["legacy"]
    assert database.users.created[0] == ("email", {"unique": True})
    assert database.document_bindings.created[-1][0] == [("user_id", 1), ("step_id", 1)]


def test_mongo_bootstrap_keeps_nonlegacy_usage_indexes() -> None:
    database = Database({"current": {"key": [("partner_id", 1), ("status", 1)]}})
    asyncio.run(initialize_mongo_schema(database))
    assert database.partner_usage_charges.dropped == []
