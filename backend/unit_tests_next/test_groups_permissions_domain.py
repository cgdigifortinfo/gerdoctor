import pytest

from slices.groups_permissions.domain import (
    AssignedGroupRoleChange, EmptyGroupName, InvalidPortalRole,
    SystemGroupRoleChange, UnknownPermission, compatible_group_ids,
    create_group_document, effective_permissions, normalize_permissions,
    permission_for_admin_request, permission_for_portal_request,
    update_group_plan, validated_permissions,
)
from slices.groups_permissions.models import GroupCreate, GroupUpdate, PermissionInputs
from slices.identity_access.models import TokenIdentity


KNOWN = frozenset({"users.view", "users.create"})


def test_effective_permissions_apply_wildcard_allow_and_deny_in_order():
    assert effective_permissions(PermissionInputs(("*",), (), ()), KNOWN) == ["*", "users.create", "users.view"]
    assert effective_permissions(PermissionInputs(("*",), ("users.create",), ("users.view",)), KNOWN) == ["users.create"]
    assert effective_permissions(PermissionInputs((), ("users.view", "unknown"), ()), KNOWN) == ["users.view"]
    assert effective_permissions(PermissionInputs((), (), (), True), KNOWN) == ["*", "users.create", "users.view"]


def test_permission_normalization_and_compatible_groups_are_deterministic():
    assert normalize_permissions(["users.view", "unknown", "users.view"], KNOWN) == ["users.view"]
    assert normalize_permissions(["*"], KNOWN) == []
    assert compatible_group_ids(["a", "", "b", "a"], ["a"], "fallback") == ["a", "a"]
    assert compatible_group_ids(["foreign"], [], "fallback") == ["fallback"]
    assert compatible_group_ids([], [], None) == []
    assert TokenIdentity("u", "e", "user").role == "user"


def test_group_creation_and_permission_validation_are_normalized():
    assert validated_permissions(["users.view", "users.view", "*"], "admin", KNOWN) == ["users.view", "*"]
    with pytest.raises(UnknownPermission) as unknown:
        validated_permissions(["zeta", "alpha"], "user", KNOWN)
    assert unknown.value.args == ("alpha, zeta",)
    document = create_group_document(GroupCreate(" Team ", " Desc ", "user", ("users.view",)), "key", "now")
    assert document == {
        "key": "key", "name": "Team", "name_key": "team", "description": "Desc",
        "role": "user", "permissions": ["users.view"], "is_system": False,
        "created_at": "now", "updated_at": "now",
    }
    with pytest.raises(EmptyGroupName):
        create_group_document(GroupCreate(" ", "", "user", ()), "key", "now")
    with pytest.raises(InvalidPortalRole) as invalid_create_role:
        create_group_document(GroupCreate("Team", "", "root", ()), "key", "now")
    assert invalid_create_role.value.args == ("root",)


def test_group_update_plan_protects_roles_and_builds_partial_update():
    current = {"name": "Old", "role": "user", "is_system": False}
    plan = update_group_plan(current, GroupUpdate(" New ", " Desc ", "partner", ("users.view",)), 0, "now")
    assert plan.role == "partner" and plan.role_changed is True
    assert plan.fields == {
        "name": "New", "name_key": "new", "role": "partner", "description": "Desc",
        "permissions": ["users.view"], "updated_at": "now",
    }
    unchanged = update_group_plan(current, GroupUpdate(), 7, "later")
    assert unchanged.fields == {"updated_at": "later"} and unchanged.role_changed is False
    partner = update_group_plan({"role": "partner"}, GroupUpdate(), 0, "now")
    assert partner.role == "partner"
    fallback = update_group_plan({}, GroupUpdate(), 0, "now")
    assert fallback.role == "user"
    same_role = update_group_plan(current, GroupUpdate(role="user"), 0, "now")
    assert same_role.role_changed is False
    with pytest.raises(EmptyGroupName): update_group_plan(current, GroupUpdate(name=" "), 0, "now")
    with pytest.raises(InvalidPortalRole) as invalid_update_role: update_group_plan(current, GroupUpdate(role="root"), 0, "now")
    assert invalid_update_role.value.args == ("root",)
    with pytest.raises(SystemGroupRoleChange): update_group_plan({**current, "is_system": True}, GroupUpdate(role="partner"), 0, "now")
    with pytest.raises(AssignedGroupRoleChange): update_group_plan(current, GroupUpdate(role="partner"), 1, "now")


@pytest.mark.parametrize("method,path,expected", [
    ("GET", "/api/admin", "admin.access"), ("GET", "/api/admin/permission-catalog", "groups.view"),
    ("GET", "/api/admin/permission-groups", "groups.view"), ("POST", "/api/admin/permission-groups", "groups.create"),
    ("DELETE", "/api/admin/permission-groups/x", "groups.delete"), ("PUT", "/api/admin/permission-groups/x", "groups.update"),
    ("GET", "/api/admin/impersonate/x", "users.impersonate"), ("GET", "/api/admin/export/users", "users.export"),
    ("PUT", "/api/admin/users/x/permissions", "users.permissions.manage"), ("PUT", "/api/admin/users/x", "users.update"),
    ("GET", "/api/admin/surveys", "surveys.view"), ("POST", "/api/admin/surveys", "surveys.manage"),
    ("GET", "/api/admin/step-templates", "steps.view"), ("GET", "/api/admin/partners", "partners.view"),
    ("POST", "/api/admin/partners", "partners.manage"), ("GET", "/api/admin/billing", "settings.view"),
    ("POST", "/api/admin/billing", "settings.manage"), ("GET", "/api/admin/analytics", "analytics.view"),
    ("GET", "/api/admin/audit-log", "audit.view"), ("GET", "/api/admin/events", "messages.view"),
    ("PATCH", "/api/admin/email-templates/x", "messages.manage"), ("GET", "/unrelated", None),
    ("GET", "/api/admin/event-configs", "messages.view"),
])
def test_all_admin_permission_routes(method, path, expected):
    assert permission_for_admin_request(method, path) == expected


@pytest.mark.parametrize("method,path,expected", [
    ("POST", "/api/cms/page", "cms.manage"), ("GET", "/api/cms/page", None),
    ("PATCH", "/api/cms/page", "cms.manage"),
    ("DELETE", "/api/steps/progress", "survey.own.submit"),
    ("PUT", "/api/profile", "profile.self.manage"),
    ("PUT", "/api/notifications/preferences", "profile.self.manage"),
    ("POST", "/api/partners/submit-multi", "survey.own.submit"),
    ("POST", "/api/partners/p/submit", "survey.own.submit"),
    ("GET", "/api/partners/p", None), ("GET", "/api/files/f", "files.own.manage"),
    ("GET", "/api/partner/profile", "partner.users.view"), ("POST", "/unrelated", None),
    ("POST", "/api/partner/logo", "profile.self.manage"),
    ("PATCH", "/api/partner/users/u", "partner.users.manage"),
])
def test_all_portal_permission_routes(method, path, expected):
    assert permission_for_portal_request(method, path) == expected
