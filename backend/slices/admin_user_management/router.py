"""FastAPI routes backed by the administrative user lifecycle service."""
from __future__ import annotations
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from slices.admin_user_management.listing_service import AdminUserListingService
from slices.admin_user_management.models import CreateUserCommand
from slices.admin_user_management.progress import (
    AdminProgressStepNotFound,
    AdminUserProgressService,
)
from slices.admin_user_management.service import AdminUserManagementService
from slices.admin_user_management.web import (
    AdminUserCreate, AdminUserProgressUpdate, BulkRoleUpdate, UserPermissionsUpdate,
    admin_user_http_error,
)

Actor=Mapping[str,Any]; Guard=Callable[[str],Callable[[Request],Awaitable[Actor]]]
Permission=Callable[[Actor,str],Awaitable[bool]]
Audit=Callable[[object,object,str,str,object,Mapping[str,Any]],Awaitable[None]]
ValidatePermissions=Callable[[Sequence[str]],list[str]]
EffectivePermissions=Callable[[Mapping[str,Any]],Awaitable[list[str]]]

def build_admin_user_management_router(service: AdminUserManagementService,
    listing: AdminUserListingService, progress: AdminUserProgressService,
    require_role: Guard,
    has_permission: Permission, validate_permissions: ValidatePermissions,
    effective_permissions: EffectivePermissions, audit: Audit) -> APIRouter:
    router=APIRouter(prefix="/admin",tags=["admin"])

    @router.get("/users")
    async def users(request: Request) -> list[dict[str, Any]]:
        await require_role("admin")(request)
        return await listing.users()

    async def require_permissions_management(actor: Actor, needed: bool) -> None:
        if needed and not await has_permission(actor,"users.permissions.manage"):
            raise HTTPException(403,"Missing permission: users.permissions.manage")
    @router.get("/users/search")
    async def search(request: Request,q: str="",role: str="") -> list[dict[str,Any]]:
        await require_role("admin")(request); return await service.search(q,role)
    @router.post("/users")
    async def create(data: AdminUserCreate,request: Request) -> dict[str,Any]:
        actor=await require_role("admin")(request); await require_permissions_management(actor,data.role=="admin" or bool(data.group_ids))
        try: result=await service.create(CreateUserCommand(str(data.email),data.password,data.name,data.role,
            data.partner_id,data.survey_id,tuple(data.group_ids or ())),actor)
        except Exception as error: raise admin_user_http_error(error)
        return result.to_document()

    @router.get("/users/{user_id}")
    async def detail(user_id: str, request: Request) -> dict[str, Any]:
        await require_role("admin")(request)
        result = await listing.detail(user_id)
        if result is None:
            raise HTTPException(404, "User not found")
        return result

    @router.put("/users/{user_id}/progress")
    async def update_progress(
        user_id: str, data: AdminUserProgressUpdate, request: Request,
    ) -> dict[str, str]:
        actor = await require_role("admin")(request)
        try:
            await progress.update(user_id, data.step_id, data.status, data.data, actor)
        except AdminProgressStepNotFound as error:
            raise HTTPException(404, "Step not found") from error
        return {"message": "User progress updated"}
    @router.put("/users/{user_id}/permissions")
    async def permissions(user_id: str,data: UserPermissionsUpdate,request: Request) -> dict[str,Any]:
        actor=await require_role("admin")(request)
        if not ObjectId.is_valid(user_id): raise HTTPException(400,"Invalid user id")
        try: groups,overrides=await service.update_permissions(user_id,data.group_ids,data.allow,data.deny,validate_permissions)
        except Exception as error: raise admin_user_http_error(error)
        saved=await service.user(user_id)
        await audit(actor["_id"],actor["email"],"user_permissions_update","user",user_id,{"group_ids":groups,**overrides})
        return {"message":"User permissions updated","group_ids":groups,"permission_overrides":overrides,
                "effective_permissions":await effective_permissions(saved or {})}
    @router.put("/users/bulk-role")
    async def bulk_role(data: BulkRoleUpdate,request: Request) -> dict[str,str]:
        actor=await require_role("admin")(request); await require_permissions_management(actor,data.role=="admin")
        try: updated=await service.bulk_role(data.user_ids,data.role)
        except Exception as error: raise admin_user_http_error(error)
        return {"message":f"{updated} users updated to {data.role}"}
    @router.put("/users/{user_id}/role")
    async def role(user_id: str,role: str,request: Request) -> dict[str,str]:
        actor=await require_role("admin")(request); await require_permissions_management(actor,role=="admin")
        try: await service.change_role(user_id,role,actor)
        except Exception as error: raise admin_user_http_error(error)
        return {"message":"User role updated"}
    @router.delete("/users/{user_id}")
    async def archive(user_id: str,request: Request) -> dict[str,str]:
        actor=await require_role("admin")(request)
        try: await service.archive(user_id,actor)
        except Exception as error: raise admin_user_http_error(error)
        return {"message":"User archived"}

    @router.get("/export/users")
    async def export(request: Request) -> Response:
        await require_role("admin")(request)
        return Response(
            content=await listing.csv_export(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=users_export.csv"},
        )
    return router
