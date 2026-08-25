"""FastAPI access-policy middleware composition."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from bson import ObjectId
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse


User = Mapping[str, Any]
PermissionResolver = Callable[[str, str], str | None]
CurrentUser = Callable[[Request], Awaitable[User]]
HasPermission = Callable[[User, str], Awaitable[bool]]
AwaitingAssignment = Callable[[Mapping[str, Any] | None], bool]


def install_access_middleware(
    app: FastAPI, database: Any, admin_permission: PermissionResolver,
    portal_permission: PermissionResolver, current_user: CurrentUser,
    has_permission: HasPermission, awaiting_assignment: AwaitingAssignment,
) -> None:
    @app.middleware("http")
    async def enforce_admin_permissions(request: Request, call_next: Any) -> Any:
        required_admin = admin_permission(request.method, request.url.path)
        permission = required_admin or portal_permission(request.method, request.url.path)
        if not permission:
            return await call_next(request)
        try:
            user = await current_user(request)
        except HTTPException as error:
            return JSONResponse(status_code=error.status_code, content={"detail": error.detail})
        if required_admin and user.get("role") != "admin" or not await has_permission(user, permission):
            return JSONResponse(status_code=403, content={"detail": f"Missing permission: {permission}"})
        path = request.url.path
        own_settings = {"/api/partner/profile", "/api/partner/partner-data"}
        pending_reads = {"/api/partner/insights"}
        partner_id = user.get("partner_id")
        if (path.startswith("/api/partner/") and path not in own_settings
                and user.get("role") == "partner" and partner_id
                and ObjectId.is_valid(str(partner_id))):
            partner = await database.partners.find_one(
                {"_id": ObjectId(str(partner_id))},
                {"registration_source": 1, "registration_status": 1, "is_active": 1,
                 "survey_ids": 1, "billing_status": 1},
            )
            allowed = request.method == "GET" and path in pending_reads
            if awaiting_assignment(partner) and not allowed:
                return JSONResponse(status_code=403, content={"detail": "Partner account is awaiting survey assignment"})
        request.state.current_user = user
        return await call_next(request)
