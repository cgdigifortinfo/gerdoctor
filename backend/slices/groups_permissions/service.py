"""Application service for permission-group administration."""
from __future__ import annotations

from slices.groups_permissions.domain import (
    AssignedGroupRoleChange, EmptyGroupName, GroupRuleError, InvalidPortalRole,
    SystemGroupRoleChange, UnknownPermission, create_group_document,
    update_group_plan, validated_permissions,
)
from slices.groups_permissions.models import GroupCreate, GroupUpdate
from slices.groups_permissions.ports import GroupsPermissionsRepository


class GroupsPermissionsError(ValueError): pass
class UnknownGroup(GroupsPermissionsError): pass
class DuplicateGroupName(GroupsPermissionsError): pass
class SystemGroupDeletion(GroupsPermissionsError): pass
class AssignedGroupDeletion(GroupsPermissionsError): pass


class GroupsPermissionsService:
    def __init__(self, repository: GroupsPermissionsRepository, known_permissions: frozenset[str]) -> None:
        self._repository = repository
        self._known_permissions = known_permissions

    async def list_groups(self) -> list[tuple[dict[str, object], int]]:
        groups = await self._repository.list_groups()
        return [(group, await self._repository.member_count(str(group["_id"]))) for group in groups]

    async def create(self, data: GroupCreate, key: str, timestamp: str) -> dict[str, object]:
        permissions = validated_permissions(data.permissions, data.role, self._known_permissions)
        normalized = GroupCreate(data.name, data.description, data.role, tuple(permissions))
        document = create_group_document(normalized, key, timestamp)
        if await self._repository.find_group_by_name(str(document["name_key"])):
            raise DuplicateGroupName(str(document["name"]))
        return await self._repository.insert_group(document)

    async def update(self, group_id: str, data: GroupUpdate, timestamp: str) -> tuple[dict[str, object], int]:
        group = await self._repository.find_group(group_id)
        if group is None:
            raise UnknownGroup(group_id)
        member_count = await self._repository.member_count(group_id)
        plan = update_group_plan(group, data, member_count, timestamp)
        if data.name is not None and await self._repository.find_group_by_name(data.name.strip().casefold(), group_id):
            raise DuplicateGroupName(data.name)
        fields = dict(plan.fields)
        if data.permissions is not None:
            fields["permissions"] = validated_permissions(data.permissions, plan.role, self._known_permissions)
        saved = await self._repository.update_group(group_id, fields)
        if saved is None:
            raise UnknownGroup(group_id)
        return saved, member_count

    async def delete(self, group_id: str) -> str:
        group = await self._repository.find_group(group_id)
        if group is None:
            raise UnknownGroup(group_id)
        if group.get("is_system"):
            raise SystemGroupDeletion(group_id)
        if await self._repository.member_count(group_id):
            raise AssignedGroupDeletion(group_id)
        await self._repository.delete_group(group_id)
        return str(group.get("name", ""))

    async def validate_group_ids(self, group_ids: list[str], role: str) -> list[str]:
        unique = list(dict.fromkeys(group_ids))
        compatible = await self._repository.compatible_group_ids(unique, role)
        if len(compatible) != len(unique):
            raise UnknownGroup("invalid or incompatible permission group")
        compatible_set = set(compatible)
        return [group_id for group_id in unique if group_id in compatible_set]


__all__ = [
    "AssignedGroupDeletion", "AssignedGroupRoleChange", "DuplicateGroupName",
    "EmptyGroupName", "GroupRuleError", "GroupsPermissionsError",
    "GroupsPermissionsService", "InvalidPortalRole", "SystemGroupDeletion",
    "SystemGroupRoleChange", "UnknownGroup", "UnknownPermission",
]
