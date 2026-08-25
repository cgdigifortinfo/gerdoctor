"""HTTP serialization and error mapping for groups and permissions."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

from slices.groups_permissions.service import (
    AssignedGroupDeletion, AssignedGroupRoleChange, DuplicateGroupName,
    EmptyGroupName, InvalidPortalRole, SystemGroupDeletion,
    SystemGroupRoleChange, UnknownGroup, UnknownPermission,
)

class PermissionGroupCreate(BaseModel):
    name: str
    description: str | None = ""
    role: str = "user"
    permissions: list[str] = Field(default_factory=list)

class PermissionGroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    role: str | None = None
    permissions: list[str] | None = None


def permission_group_payload(group: dict[str, Any], member_count: int = 0) -> dict[str, Any]:
    return {
        "id": str(group["_id"]), "key": group.get("key", ""),
        "name": group.get("name", ""), "description": group.get("description", ""),
        "role": group.get("role", "user"), "permissions": group.get("permissions", []),
        "is_system": group.get("is_system", False), "member_count": member_count,
        "created_at": group.get("created_at"), "updated_at": group.get("updated_at"),
    }


def groups_permissions_http_error(error: Exception) -> HTTPException:
    if isinstance(error, UnknownGroup): return HTTPException(status_code=404, detail="Permission group not found")
    if isinstance(error, DuplicateGroupName): return HTTPException(status_code=400, detail="A group with this name already exists")
    if isinstance(error, EmptyGroupName): return HTTPException(status_code=400, detail="Group name is required")
    if isinstance(error, InvalidPortalRole): return HTTPException(status_code=400, detail="Invalid portal role")
    if isinstance(error, UnknownPermission): return HTTPException(status_code=400, detail=f"Unknown permission(s): {error}")
    if isinstance(error, SystemGroupRoleChange): return HTTPException(status_code=400, detail="System group role cannot be changed")
    if isinstance(error, AssignedGroupRoleChange): return HTTPException(status_code=400, detail="Group role cannot be changed while users are assigned")
    if isinstance(error, SystemGroupDeletion): return HTTPException(status_code=400, detail="System groups cannot be deleted")
    if isinstance(error, AssignedGroupDeletion): return HTTPException(status_code=400, detail="Permission group is still assigned to users")
    return HTTPException(status_code=400, detail="Invalid groups and permissions request")
