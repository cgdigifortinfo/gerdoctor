"""Pure rules for permission evaluation and permission-group changes."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from slices.groups_permissions.models import GroupCreate, GroupUpdate, GroupUpdatePlan, PermissionInputs

PORTAL_ROLES = frozenset({"admin", "partner", "user"})


class GroupRuleError(ValueError): pass
class EmptyGroupName(GroupRuleError): pass
class InvalidPortalRole(GroupRuleError): pass
class UnknownPermission(GroupRuleError): pass
class SystemGroupRoleChange(GroupRuleError): pass
class AssignedGroupRoleChange(GroupRuleError): pass


def normalize_permissions(values: Iterable[str] | None, known: frozenset[str], allow_wildcard: bool = False) -> list[str]:
    valid = known | ({"*"} if allow_wildcard else set())
    return list(dict.fromkeys(value for value in (values or ()) if value in valid))


def validated_permissions(values: Iterable[str], role: str, known: frozenset[str]) -> list[str]:
    allowed = set(known)
    if role == "admin":
        allowed.add("*")
    unknown = sorted(set(values) - allowed)
    if unknown:
        raise UnknownPermission(", ".join(unknown))
    return normalize_permissions(values, known, allow_wildcard=role == "admin")


def effective_permissions(inputs: PermissionInputs, known: frozenset[str]) -> list[str]:
    if inputs.administrator:
        return ["*", *sorted(known)]
    permissions = set(normalize_permissions(inputs.group_permissions, known, allow_wildcard=True))
    permissions.update(normalize_permissions(inputs.allowed, known))
    denied = set(normalize_permissions(inputs.denied, known))
    if "*" in permissions:
        permissions = set(known)
        permissions.add("*")
    permissions.difference_update(denied)
    if denied:
        permissions.discard("*")
    return sorted(permissions)


def compatible_group_ids(original_ids: Iterable[str], compatible_ids: Iterable[str], fallback_id: str | None) -> list[str]:
    original = [value for value in original_ids if value]
    compatible = set(compatible_ids)
    result = [value for value in original if value in compatible]
    return result or ([fallback_id] if fallback_id else [])


def create_group_document(data: GroupCreate, key: str, timestamp: str) -> dict[str, Any]:
    name = data.name.strip()
    if not name:
        raise EmptyGroupName
    if data.role not in PORTAL_ROLES:
        raise InvalidPortalRole(data.role)
    return {
        "key": key,
        "name": name,
        "name_key": name.casefold(),
        "description": data.description.strip(),
        "role": data.role,
        "permissions": list(data.permissions),
        "is_system": False,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def update_group_plan(current: Mapping[str, Any], data: GroupUpdate, member_count: int,
                      timestamp: str) -> GroupUpdatePlan:
    fields: dict[str, object] = {}
    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise EmptyGroupName
        fields.update({"name": name, "name_key": name.casefold()})
    role = data.role if data.role is not None else str(current.get("role", "user"))
    if role not in PORTAL_ROLES:
        raise InvalidPortalRole(role)
    role_changed = data.role is not None and data.role != current.get("role")
    if role_changed and current.get("is_system"):
        raise SystemGroupRoleChange
    if role_changed and member_count:
        raise AssignedGroupRoleChange
    if data.role is not None:
        fields["role"] = data.role
    if data.description is not None:
        fields["description"] = data.description.strip()
    if data.permissions is not None:
        fields["permissions"] = list(data.permissions)
    fields["updated_at"] = timestamp
    return GroupUpdatePlan(fields, role, role_changed)


def permission_for_admin_request(method: str, path: str) -> str | None:
    if path != "/api/admin" and not path.startswith("/api/admin/"):
        return None
    relative = path[len("/api/admin"):]
    verb = method.upper()
    write = verb in {"POST", "PUT", "PATCH", "DELETE"}
    if relative.startswith("/permission-catalog"): return "groups.view"
    if relative.startswith("/permission-groups"):
        if not write: return "groups.view"
        if verb == "POST": return "groups.create"
        if verb == "DELETE": return "groups.delete"
        return "groups.update"
    if relative.startswith("/impersonate"): return "users.impersonate"
    if relative.startswith("/export/users"): return "users.export"
    if relative.startswith("/users"):
        if "/permissions" in relative: return "users.permissions.manage"
        if verb == "POST": return "users.create"
        if verb == "DELETE": return "users.delete"
        return "users.update" if write else "users.view"
    prefixes = (
        ("/surveys", "surveys"), ("/steps", "steps"), ("/step-templates", "steps"),
        ("/partners", "partners"), ("/settings", "settings"), ("/billing", "settings"),
    )
    for prefix, permission in prefixes:
        if relative.startswith(prefix): return f"{permission}.manage" if write else f"{permission}.view"
    if relative.startswith("/analytics"): return "analytics.view"
    if relative.startswith("/audit-log"): return "audit.view"
    if relative.startswith(("/email-templates", "/event-configs", "/events")):
        return "messages.manage" if write else "messages.view"
    return "admin.access"


def permission_for_portal_request(method: str, path: str) -> str | None:
    verb = method.upper()
    write = verb in {"POST", "PUT", "PATCH", "DELETE"}
    if path.startswith("/api/cms/") and write: return "cms.manage"
    if path in {"/api/profile", "/api/notifications/preferences"} and verb == "PUT":
        return "profile.self.manage"
    if path.startswith("/api/steps"): return "survey.own.submit" if write else "survey.own.view"
    if path == "/api/partners/submit-multi" or (path.startswith("/api/partners/") and path.endswith("/submit")):
        return "survey.own.submit"
    if path.startswith("/api/files"): return "files.own.manage"
    if path.startswith("/api/partner/"):
        if path == "/api/partner/profile" and verb == "PUT": return "profile.self.manage"
        return "partner.users.manage" if write else "partner.users.view"
    return None
