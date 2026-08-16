"""Exhaustive unit coverage for RBAC assignment and request enforcement."""
import asyncio

import pytest
from bson import ObjectId

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
        if "_id" in query:
            return next((row for row in self.rows if row["_id"] == query["_id"]), None)
        if "key" in query:
            return next((row for row in self.rows if row.get("key") == query["key"]), None)
        return None


class FakeDb:
    def __init__(self, groups):
        self.permission_groups = GroupCollection(groups)


ADMIN_REQUEST_CASES = [
    ("GET", "/api/admin", "admin.access"),
    ("GET", "/api/admin/analytics", "analytics.view"),
    ("GET", "/api/admin/audit-log", "audit.view"),
    ("GET", "/api/admin/users", "users.view"),
    ("GET", "/api/admin/users/search", "users.view"),
    ("GET", "/api/admin/users/507f1f77bcf86cd799439011", "users.view"),
    ("POST", "/api/admin/users", "users.create"),
    ("PUT", "/api/admin/users/507f1f77bcf86cd799439011/role", "users.update"),
    ("PUT", "/api/admin/users/507f1f77bcf86cd799439011/progress", "users.update"),
    ("PUT", "/api/admin/users/bulk-role", "users.update"),
    ("DELETE", "/api/admin/users/507f1f77bcf86cd799439011", "users.delete"),
    ("POST", "/api/admin/impersonate/507f1f77bcf86cd799439011", "users.impersonate"),
    ("GET", "/api/admin/export/users", "users.export"),
    ("PUT", "/api/admin/users/507f1f77bcf86cd799439011/permissions", "users.permissions.manage"),
    ("GET", "/api/admin/permission-catalog", "groups.view"),
    ("GET", "/api/admin/permission-groups", "groups.view"),
    ("POST", "/api/admin/permission-groups", "groups.create"),
    ("PUT", "/api/admin/permission-groups/507f1f77bcf86cd799439011", "groups.update"),
    ("DELETE", "/api/admin/permission-groups/507f1f77bcf86cd799439011", "groups.delete"),
    ("GET", "/api/admin/surveys", "surveys.view"),
    ("POST", "/api/admin/surveys", "surveys.manage"),
    ("PUT", "/api/admin/surveys/507f1f77bcf86cd799439011", "surveys.manage"),
    ("GET", "/api/admin/steps", "steps.view"),
    ("GET", "/api/admin/step-templates", "steps.view"),
    ("POST", "/api/admin/steps", "steps.manage"),
    ("PUT", "/api/admin/steps/reorder", "steps.manage"),
    ("DELETE", "/api/admin/step-templates/507f1f77bcf86cd799439011", "steps.manage"),
    ("GET", "/api/admin/partners", "partners.view"),
    ("POST", "/api/admin/partners", "partners.manage"),
    ("PUT", "/api/admin/partners/507f1f77bcf86cd799439011/link-user", "partners.manage"),
    ("DELETE", "/api/admin/partners/507f1f77bcf86cd799439011", "partners.manage"),
    ("GET", "/api/admin/email-templates", "messages.view"),
    ("GET", "/api/admin/event-configs", "messages.view"),
    ("GET", "/api/admin/events", "messages.view"),
    ("PUT", "/api/admin/email-templates/welcome", "messages.manage"),
    ("PUT", "/api/admin/event-configs/user.created", "messages.manage"),
    ("POST", "/api/admin/events/507f1f77bcf86cd799439011/retry", "messages.manage"),
    ("GET", "/api/admin/settings", "settings.view"),
    ("PUT", "/api/admin/settings", "settings.manage"),
]

PORTAL_REQUEST_CASES = [
    ("PUT", "/api/cms/home", "cms.manage"),
    ("PUT", "/api/profile", "profile.self.manage"),
    ("PUT", "/api/notifications/preferences", "profile.self.manage"),
    ("GET", "/api/steps", "survey.own.view"),
    ("GET", "/api/steps/bootstrap", "survey.own.view"),
    ("GET", "/api/steps/history", "survey.own.view"),
    ("PUT", "/api/steps/progress", "survey.own.submit"),
    ("POST", "/api/partners/submit", "survey.own.submit"),
    ("POST", "/api/partners/submit-multi", "survey.own.submit"),
    ("GET", "/api/files/fixture", "files.own.manage"),
    ("POST", "/api/files/upload", "files.own.manage"),
    ("GET", "/api/partner/submissions", "partner.users.view"),
    ("GET", "/api/partner/users/507f1f77bcf86cd799439011", "partner.users.view"),
    ("PUT", "/api/partner/profile", "profile.self.manage"),
    ("PUT", "/api/partner/users/507f1f77bcf86cd799439011/progress", "partner.users.manage"),
    ("POST", "/api/partner/users/507f1f77bcf86cd799439011/complete", "partner.users.manage"),
]

# These permissions guard frontend entry points or read-only UI visibility.
# Their presence in the default groups is asserted below; the underlying public
# CMS reads intentionally do not require authentication.
UI_ONLY_PERMISSIONS = {"portal.user.access", "portal.partner.access", "cms.view"}


def test_normalize_permissions_removes_unknown_values_and_duplicates():
    assert permissions.normalize_permissions([
        "users.view", "invalid", "users.view", "*"
    ]) == ["users.view"]
    assert permissions.normalize_permissions(["users.view", "*"], allow_wildcard=True) == ["users.view", "*"]


def test_catalog_keys_are_unique_valid_and_every_permission_has_a_guard_case():
    catalog_keys = [
        item["key"]
        for category in permissions.PERMISSION_CATALOG
        for item in category["permissions"]
    ]
    guarded = {expected for _, _, expected in ADMIN_REQUEST_CASES + PORTAL_REQUEST_CASES}

    assert len(catalog_keys) == len(set(catalog_keys))
    assert tuple(catalog_keys) == permissions.ALL_PERMISSION_KEYS
    assert set(catalog_keys) == guarded | UI_ONLY_PERMISSIONS
    assert not guarded & UI_ONLY_PERMISSIONS


@pytest.mark.parametrize("method,path,expected", ADMIN_REQUEST_CASES)
def test_every_admin_request_is_mapped_to_its_exact_permission(method, path, expected):
    assert permissions.permission_for_admin_request(method, path) == expected


@pytest.mark.parametrize("method,path,expected", PORTAL_REQUEST_CASES)
def test_every_portal_request_is_mapped_to_its_exact_permission(method, path, expected):
    assert permissions.permission_for_portal_request(method, path) == expected


@pytest.mark.parametrize("method,path", [
    ("GET", "/api/administrator"),
    ("GET", "/api/profile"),
    ("GET", "/api/cms/home"),
    ("GET", "/api/partners"),
    ("GET", "/api/partners/507f1f77bcf86cd799439011"),
    ("POST", "/api/auth/login"),
])
def test_public_or_auth_only_requests_do_not_receive_an_unrelated_permission(method, path):
    assert permissions.permission_for_admin_request(method, path) is None
    assert permissions.permission_for_portal_request(method, path) is None


@pytest.mark.parametrize("permission", permissions.ALL_PERMISSION_KEYS)
def test_each_catalog_permission_can_be_granted_and_explicitly_denied(monkeypatch, permission):
    group_id = ObjectId()
    monkeypatch.setattr(permissions, "db", FakeDb([
        {"_id": group_id, "permissions": [permission]},
    ]))
    user = {
        "email": "permission-check@example.test",
        "role": "admin",
        "group_ids": [str(group_id)],
        "permission_overrides": {"allow": [], "deny": []},
    }

    assert asyncio.run(permissions.has_permission(user, permission)) is True

    user["permission_overrides"] = {"allow": [permission], "deny": [permission]}
    assert asyncio.run(permissions.has_permission(user, permission)) is False


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


def test_wildcard_grants_every_permission_and_deny_removes_only_selected_right(monkeypatch):
    group_id = ObjectId()
    monkeypatch.setattr(permissions, "db", FakeDb([
        {"_id": group_id, "permissions": ["*"]},
    ]))
    user = {
        "email": "wildcard-admin@example.test",
        "role": "admin",
        "group_ids": [str(group_id)],
        "permission_overrides": {"allow": [], "deny": ["users.delete"]},
    }

    effective = set(asyncio.run(permissions.effective_permissions(user)))

    assert "*" not in effective
    assert "users.delete" not in effective
    assert effective == set(permissions.ALL_PERMISSION_KEYS) - {"users.delete"}


@pytest.mark.parametrize("role,expected", [
    ("admin", set(permissions.ALL_PERMISSION_KEYS) | {"*"}),
    ("user", {"portal.user.access", "profile.self.manage", "survey.own.view", "survey.own.submit", "files.own.manage"}),
    ("partner", {"portal.partner.access", "profile.self.manage", "partner.users.view", "partner.users.manage", "files.own.manage"}),
])
def test_legacy_users_receive_the_role_default_until_migrated(monkeypatch, role, expected):
    monkeypatch.setattr(permissions, "db", FakeDb([]))
    user = {"email": f"legacy-{role}@example.test", "role": role, "group_ids": []}

    assert set(asyncio.run(permissions.effective_permissions(user))) == expected


def test_migrated_user_with_no_groups_has_no_implicit_permissions(monkeypatch):
    monkeypatch.setattr(permissions, "db", FakeDb([]))
    user = {
        "email": "no-groups@example.test",
        "role": "admin",
        "group_ids": [],
        "permission_overrides": {"allow": [], "deny": []},
    }

    assert asyncio.run(permissions.effective_permissions(user)) == []


def test_invalid_and_missing_group_ids_are_ignored_without_granting_rights(monkeypatch):
    monkeypatch.setattr(permissions, "db", FakeDb([]))
    user = {
        "email": "invalid-groups@example.test",
        "role": "user",
        "group_ids": ["not-an-object-id", str(ObjectId())],
        "permission_overrides": {"allow": ["survey.own.view", "unknown.permission"], "deny": []},
    }

    assert asyncio.run(permissions.effective_permissions(user)) == ["survey.own.view"]


@pytest.mark.parametrize("role,key", [
    ("admin", "administrators"),
    ("user", "survey_users"),
    ("partner", "partners"),
])
def test_default_group_lookup_uses_the_portal_role(monkeypatch, role, key):
    rows = [
        {"_id": ObjectId(), "key": definition["key"], "permissions": definition["permissions"]}
        for definition in permissions.DEFAULT_GROUPS
    ]
    monkeypatch.setattr(permissions, "db", FakeDb(rows))

    group_id = asyncio.run(permissions.default_group_id(role))

    assert group_id == str(next(row["_id"] for row in rows if row["key"] == key))


def test_default_groups_only_contain_known_permissions_and_required_portal_access():
    defaults = {group["role"]: group for group in permissions.DEFAULT_GROUPS}

    for group in permissions.DEFAULT_GROUPS:
        assert group["permissions"] == ["*"] or set(group["permissions"]).issubset(permissions.ALL_PERMISSION_SET)
    assert "*" in defaults["admin"]["permissions"]
    assert "portal.user.access" in defaults["user"]["permissions"]
    assert "portal.partner.access" in defaults["partner"]["permissions"]


def test_primary_admin_cannot_be_locked_out(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "owner@example.test")
    monkeypatch.setattr(permissions, "db", FakeDb([]))
    effective = asyncio.run(permissions.effective_permissions({
        "email": "owner@example.test",
        "role": "admin",
        "group_ids": [],
        "permission_overrides": {"allow": [], "deny": list(permissions.ALL_PERMISSION_KEYS)},
    }))

    assert "*" in effective
    assert set(permissions.ALL_PERMISSION_KEYS).issubset(set(effective))
