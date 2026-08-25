from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from bson import ObjectId

from slices.groups_permissions.models import GroupCreate, GroupUpdate
from slices.groups_permissions.repository import MongoGroupsPermissionsRepository
from slices.groups_permissions.service import (
    AssignedGroupDeletion, DuplicateGroupName, GroupsPermissionsService,
    SystemGroupDeletion, UnknownGroup,
)
from slices.groups_permissions.web import groups_permissions_http_error, permission_group_payload
from slices.groups_permissions.domain import (
    AssignedGroupRoleChange, EmptyGroupName, InvalidPortalRole,
    SystemGroupRoleChange, UnknownPermission,
)


KNOWN = frozenset({"users.view", "users.create"})


class Repository:
    def __init__(self) -> None:
        self.group: dict[str, Any] | None = {"_id": "g", "name": "Group", "role": "user", "is_system": False}
        self.duplicate: dict[str, Any] | None = None
        self.members = 0
        self.groups = [self.group]
        self.compatible = ["g"]
        self.update_none = False
        self.calls: list[tuple[Any, ...]] = []

    async def list_groups(self): return [group for group in self.groups if group]  # type: ignore[no-untyped-def]
    async def find_group(self, group_id): return self.group  # type: ignore[no-untyped-def]
    async def find_group_by_name(self, name_key, excluding_id=None): return self.duplicate  # type: ignore[no-untyped-def]
    async def member_count(self, group_id): return self.members  # type: ignore[no-untyped-def]
    async def insert_group(self, document): self.calls.append(("insert", document)); return {**document, "_id": "new"}  # type: ignore[no-untyped-def]
    async def update_group(self, group_id, fields): self.calls.append(("update", fields)); return None if self.update_none else {**self.group, **fields} if self.group else None  # type: ignore[no-untyped-def]
    async def delete_group(self, group_id): self.calls.append(("delete", group_id))  # type: ignore[no-untyped-def]
    async def compatible_group_ids(self, group_ids, role): return self.compatible  # type: ignore[no-untyped-def]


def test_service_covers_group_lifecycle_and_assignment_validation():
    async def scenario() -> None:
        repository = Repository()
        service = GroupsPermissionsService(repository, KNOWN)
        listed = await service.list_groups()
        assert listed[0][1] == 0
        created = await service.create(GroupCreate(" Team ", "", "user", ("users.view",)), "custom", "now")
        assert created["name"] == "Team"
        saved, count = await service.update("g", GroupUpdate(name=" New ", permissions=("users.create",)), "later")
        assert saved["name"] == "New" and count == 0
        assert await service.validate_group_ids(["g", "g"], "user") == ["g"]
        assert await service.delete("g") == "Group"
        assert ("delete", "g") in repository.calls
    asyncio.run(scenario())


def test_service_rejects_duplicates_missing_groups_and_protected_deletion():
    async def scenario() -> None:
        repository = Repository()
        service = GroupsPermissionsService(repository, KNOWN)
        repository.duplicate = {"_id": "other"}
        with pytest.raises(DuplicateGroupName): await service.create(GroupCreate("Group", "", "user", ()), "k", "now")
        with pytest.raises(DuplicateGroupName): await service.update("g", GroupUpdate(name="Other"), "now")
        repository.duplicate = None
        repository.compatible = []
        with pytest.raises(UnknownGroup): await service.validate_group_ids(["g"], "user")
        repository.group = None
        with pytest.raises(UnknownGroup): await service.update("g", GroupUpdate(), "now")
        with pytest.raises(UnknownGroup): await service.delete("g")
        repository.group = {"_id": "g", "name": "System", "role": "user", "is_system": True}
        with pytest.raises(SystemGroupDeletion): await service.delete("g")
        repository.group["is_system"] = False
        repository.members = 1
        with pytest.raises(AssignedGroupDeletion): await service.delete("g")
        repository.members = 0
        repository.group = {"_id": "g", "name": "Group", "role": "user", "is_system": False}
        repository.update_none = True
        with pytest.raises(UnknownGroup): await service.update("g", GroupUpdate(), "now")
    asyncio.run(scenario())


class Cursor:
    def __init__(self, rows): self.rows = rows  # type: ignore[no-untyped-def]
    def sort(self, specification): return self  # type: ignore[no-untyped-def]
    async def to_list(self, limit): return self.rows  # type: ignore[no-untyped-def]
    def __aiter__(self): self.iterator = iter(self.rows); return self
    async def __anext__(self):
        try: return next(self.iterator)
        except StopIteration as error: raise StopAsyncIteration from error


class Collection:
    def __init__(self) -> None: self.calls = []; self.rows = [{"_id": ObjectId(), "name": "G"}]  # type: ignore[var-annotated]
    def find(self, query, projection=None): self.calls.append(("find", query, projection)); return Cursor(self.rows)  # type: ignore[no-untyped-def]
    async def find_one(self, query): self.calls.append(("find_one", query)); return self.rows[0]  # type: ignore[no-untyped-def]
    async def count_documents(self, query): return 1  # type: ignore[no-untyped-def]
    async def insert_one(self, document): return SimpleNamespace(inserted_id=ObjectId())  # type: ignore[no-untyped-def]
    async def update_one(self, query, operation): self.calls.append(("update", query, operation))  # type: ignore[no-untyped-def]
    async def delete_one(self, query): self.calls.append(("delete", query))  # type: ignore[no-untyped-def]


def test_mongo_repository_handles_valid_invalid_and_empty_identifiers():
    async def scenario() -> None:
        database = SimpleNamespace(permission_groups=Collection(), users=Collection())
        repository = MongoGroupsPermissionsRepository(database)
        group_id = str(ObjectId())
        assert len(await repository.list_groups()) == 1
        assert await repository.find_group(group_id) is not None and await repository.find_group("bad") is None
        assert await repository.find_group_by_name("group") is not None
        assert await repository.find_group_by_name("group", group_id) is not None
        assert await repository.member_count(group_id) == 1
        assert (await repository.insert_group({"name": "G"}))["_id"]
        assert await repository.update_group(group_id, {"name": "N"}) is not None
        assert await repository.update_group("bad", {}) is None
        await repository.delete_group(group_id)
        await repository.delete_group("bad")
        assert await repository.compatible_group_ids([group_id], "user")
        assert await repository.compatible_group_ids(["bad"], "user") == []
    asyncio.run(scenario())


def test_web_payload_and_all_error_mappings_are_stable():
    payload = permission_group_payload({"_id": "g", "name": "G"}, 2)
    assert payload["id"] == "g" and payload["member_count"] == 2 and payload["role"] == "user"
    errors = [
        UnknownGroup(), DuplicateGroupName(), EmptyGroupName(), InvalidPortalRole(),
        UnknownPermission("x"), SystemGroupRoleChange(), AssignedGroupRoleChange(),
        SystemGroupDeletion(), AssignedGroupDeletion(), ValueError(),
    ]
    assert [groups_permissions_http_error(error).status_code for error in errors] == [404, 400, 400, 400, 400, 400, 400, 400, 400, 400]
