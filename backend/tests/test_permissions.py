"""Unit coverage for RBAC group resolution and route enforcement."""
from bson import ObjectId
import asyncio

try:
    import backend.permissions as permissions
except ModuleNotFoundError:
    import permissions


class AsyncCursor:
    def __init__(self, rows):
        self.rows = rows

    def __aiter__(self):
        self.iterator = iter(self.rows)
        return self

    async def __anext__(self):
        try:
            return next(self.iterator)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class GroupCollection:
    def __init__(self, rows):
        self.rows = rows

    def find(self, query):
        ids = set(query["_id"]["$in"])
        return AsyncCursor([row for row in self.rows if row["_id"] in ids])

    async def find_one(self, query):
        return next((row for row in self.rows if row["_id"] == query.get("_id")), None)


class FakeDb:
    def __init__(self, groups):
        self.permission_groups = GroupCollection(groups)


def test_normalize_permissions_removes_unknown_values_and_duplicates():
    assert permissions.normalize_permissions([
        "users.view", "invalid", "users.view", "*"
    ]) == ["users.view"]
    assert permissions.normalize_permissions(["users.view", "*"], allow_wildcard=True) == ["users.view", "*"]


def test_permission_route_mapping_distinguishes_crud_actions():
    assert permissions.permission_for_admin_request("GET", "/api/admin/users") == "users.view"
    assert permissions.permission_for_admin_request("POST", "/api/admin/users") == "users.create"
    assert permissions.permission_for_admin_request("DELETE", "/api/admin/users/abc") == "users.delete"
    assert permissions.permission_for_admin_request("PUT", "/api/admin/users/abc/permissions") == "users.permissions.manage"
    assert permissions.permission_for_admin_request("GET", "/api/admin/permission-groups") == "groups.view"
    assert permissions.permission_for_admin_request("POST", "/api/admin/permission-groups") == "groups.create"
    assert permissions.permission_for_portal_request("PUT", "/api/steps/progress") == "survey.own.submit"
    assert permissions.permission_for_portal_request("GET", "/api/partners") is None
    assert permissions.permission_for_portal_request("POST", "/api/partners/submit-multi") == "survey.own.submit"


def test_effective_permissions_union_groups_and_apply_deny_last(monkeypatch):
    first_id, second_id = ObjectId(), ObjectId()
    monkeypatch.setattr(permissions, "db", FakeDb([
        {"_id": first_id, "permissions": ["admin.access", "users.view", "users.update"]},
        {"_id": second_id, "permissions": ["users.export"]},
    ]))
    user = {
        "email": "limited-admin@test.de",
        "role": "admin",
        "group_ids": [str(first_id), str(second_id)],
        "permission_overrides": {
            "allow": ["users.create"],
            "deny": ["users.view"],
        },
    }

    effective = asyncio.run(permissions.effective_permissions(user))

    assert "admin.access" in effective
    assert "users.update" in effective
    assert "users.export" in effective
    assert "users.create" in effective
    assert "users.view" not in effective


def test_primary_admin_cannot_be_locked_out(monkeypatch):
    monkeypatch.setattr(permissions, "db", FakeDb([]))
    effective = asyncio.run(permissions.effective_permissions({
        "email": "admin@example.com",
        "role": "admin",
        "group_ids": [],
        "permission_overrides": {"allow": [], "deny": list(permissions.ALL_PERMISSION_KEYS)},
    }))

    assert "*" in effective
    assert set(permissions.ALL_PERMISSION_KEYS).issubset(set(effective))
