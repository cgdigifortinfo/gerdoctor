"""FastAPI administration routes for permission groups."""
from __future__ import annotations
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any
from fastapi import APIRouter, Request
from slices.groups_permissions.models import GroupCreate, GroupUpdate
from slices.groups_permissions.service import GroupsPermissionsService
from slices.groups_permissions.web import (
    PermissionGroupCreate, PermissionGroupUpdate, groups_permissions_http_error,
    permission_group_payload,
)

Actor = Mapping[str, Any]
Guard = Callable[[str], Callable[[Request], Awaitable[Actor]]]
Audit = Callable[[object, object, str, str, object, Mapping[str, Any]], Awaitable[None]]

def build_groups_permissions_router(service: GroupsPermissionsService, require_role: Guard,
                                    audit: Audit, permission_catalog: Sequence[Mapping[str, Any]],
                                    permission_keys: frozenset[str], new_id: Callable[[], str],
                                    now: Callable[[], str]) -> APIRouter:
    router = APIRouter(prefix="/admin", tags=["admin"])
    @router.get("/permission-catalog")
    async def catalog(request: Request) -> dict[str, Any]:
        await require_role("admin")(request)
        return {"categories": list(permission_catalog), "all_permissions": list(permission_keys)}
    @router.get("/permission-groups")
    async def groups(request: Request) -> list[dict[str, Any]]:
        await require_role("admin")(request)
        return [permission_group_payload(group, count) for group, count in await service.list_groups()]
    @router.post("/permission-groups")
    async def create(data: PermissionGroupCreate, request: Request) -> dict[str, Any]:
        actor = await require_role("admin")(request)
        try:
            document = await service.create(GroupCreate(data.name, data.description or "", data.role,
                                                        tuple(data.permissions)), f"custom_{new_id()}", now())
        except Exception as error: raise groups_permissions_http_error(error)
        group_id = str(document["_id"])
        await audit(actor["_id"], actor["email"], "permission_group_create", "permission_group", group_id,
                    {"name": document["name"], "role": document["role"]})
        return permission_group_payload(document)
    @router.put("/permission-groups/{group_id}")
    async def update(group_id: str, data: PermissionGroupUpdate, request: Request) -> dict[str, Any]:
        actor = await require_role("admin")(request)
        command = GroupUpdate(data.name, data.description, data.role,
                              tuple(data.permissions) if data.permissions is not None else None)
        try: saved, count = await service.update(group_id, command, now())
        except Exception as error: raise groups_permissions_http_error(error)
        fields = [name for name in ("name", "description", "role", "permissions") if getattr(data, name) is not None]
        fields.append("updated_at")
        await audit(actor["_id"], actor["email"], "permission_group_update", "permission_group", group_id,
                    {"fields": fields})
        return permission_group_payload(saved, count)
    @router.delete("/permission-groups/{group_id}")
    async def delete(group_id: str, request: Request) -> dict[str, str]:
        actor = await require_role("admin")(request)
        try: name = await service.delete(group_id)
        except Exception as error: raise groups_permissions_http_error(error)
        await audit(actor["_id"], actor["email"], "permission_group_delete", "permission_group", group_id, {"name": name})
        return {"message": "Permission group deleted"}
    return router
