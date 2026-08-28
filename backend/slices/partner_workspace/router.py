"""FastAPI routes for partner profile and dashboard insights."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from slices.identity_access.service import IdentityAccessService
from slices.identity_access.web import ProfileUpdate
from slices.partner_insights.service import PartnerInsightsService
from slices.partner_workspace.profile import PartnerProfileNotLinked, PartnerProfileService
from slices.partner_workspace.logo import (
    InvalidPartnerLogo, MAX_PARTNER_LOGO_BYTES, PartnerLogoTooLarge,
)
from slices.partner_workspace.read_service import PartnerNotLinked, PartnerWorkspaceReadService
from slices.partner_workspace.detail_service import PartnerWorkspaceDetailService
from slices.partner_workspace.service import WorkspaceUserNotFound
from slices.partner_workspace.command_service import (
    ManagedMilestoneNotFound, PartnerWorkspaceCommandService,
    WorkspaceCommandStepNotFound, WorkspaceStepNotManaged,
)
from slices.survey_runtime.progress_service import ProgressCommand
from slices.survey_runtime.web import UserProgressUpdate
from slices.partner_workspace.action_service import (
    PartnerWorkspaceActionService, WorkspaceActionCommand,
    WorkspaceActionStepNotFound, WorkspaceActionStepNotManaged,
)
from slices.partner_workspace.domain import InvalidWorkspaceAction, RejectionReasonRequired
from slices.partner_workspace.web import PartnerStepAction
from slices.partner_workspace.web import PartnerSelfUpdate


Actor = Mapping[str, Any]
Guard = Callable[[str], Callable[[Request], Awaitable[Actor]]]
Audit = Callable[[object, object, str, str, object, Mapping[str, Any]], Awaitable[None]]


def build_partner_workspace_router(
    profile: PartnerProfileService, identity: IdentityAccessService,
    insights: PartnerInsightsService, require_role: Guard, audit: Audit,
    now_iso: Callable[[], str],
) -> APIRouter:
    router = APIRouter(prefix="/partner", tags=["partner"])

    @router.get("/profile")
    async def get_profile(request: Request) -> dict[str, Any]:
        return await profile.profile(await require_role("partner")(request))

    @router.put("/profile")
    async def update_profile(data: ProfileUpdate, request: Request) -> dict[str, str]:
        user = await require_role("partner")(request)
        await identity.update_profile(user["_id"], data.model_dump())
        return {"message": "Profile updated"}

    @router.put("/partner-data")
    async def update_partner_data(
        data: PartnerSelfUpdate, request: Request,
    ) -> dict[str, str]:
        user = await require_role("partner")(request)
        try:
            partner_id, fields = await profile.update_organization(
                user, data.model_dump(), now_iso(),
            )
        except PartnerProfileNotLinked as error:
            raise HTTPException(400, "User not linked to a partner") from error
        await audit(user["_id"], user["email"], "partner_self_update", "partner",
                    partner_id, {"fields": fields})
        return {"message": "Partner data updated"}

    @router.post("/logo")
    async def upload_logo(
        request: Request, file: UploadFile = File(...),
    ) -> dict[str, str]:
        user = await require_role("partner")(request)
        content = await file.read(MAX_PARTNER_LOGO_BYTES + 1)
        try:
            partner_id, logo_url = await profile.update_logo(
                user, file.filename or "", file.content_type or "", content, now_iso(),
            )
        except PartnerProfileNotLinked as error:
            raise HTTPException(400, "User not linked to a partner") from error
        except PartnerLogoTooLarge as error:
            raise HTTPException(413, "Logo must not exceed 2 MB") from error
        except InvalidPartnerLogo as error:
            raise HTTPException(415, str(error)) from error
        await audit(user["_id"], user["email"], "partner_logo_update", "partner",
                    partner_id, {"fields": ["logo_url"]})
        return {"message": "Partner logo updated", "logo_url": logo_url}

    @router.get("/insights")
    async def partner_insights(request: Request) -> dict[str, Any]:
        user = await require_role("partner")(request)
        partner_id = user.get("partner_id")
        if not partner_id:
            raise HTTPException(400, "User not linked to a partner")
        return await insights.insights(str(partner_id))

    return router


def build_partner_workspace_action_router(
    service: PartnerWorkspaceActionService, require_role: Guard,
) -> APIRouter:
    router = APIRouter(prefix="/partner/users", tags=["partner"])

    @router.post("/{user_id}/steps/{step_id}/action")
    async def action(user_id: str, step_id: str, data: PartnerStepAction,
                     request: Request) -> dict[str, Any]:
        actor = await require_role("partner")(request)
        try:
            return await service.execute(actor, user_id, step_id,
                                         WorkspaceActionCommand(data.action, data.reason, data.data))
        except PartnerNotLinked as error: raise HTTPException(400, "User not linked to a partner") from error
        except InvalidWorkspaceAction as error: raise HTTPException(400, "Action must be 'complete' or 'reject'") from error
        except RejectionReasonRequired as error: raise HTTPException(422, "A rejection reason is required") from error
        except WorkspaceActionStepNotManaged as error: raise HTTPException(403, "This step is not managed by your partner organization") from error
        except WorkspaceActionStepNotFound as error: raise HTTPException(404, "Step not found") from error
        except WorkspaceUserNotFound as error: raise HTTPException(404, "User not found") from error

    return router


def build_partner_workspace_command_router(
    service: PartnerWorkspaceCommandService, require_role: Guard,
) -> APIRouter:
    router = APIRouter(prefix="/partner/users", tags=["partner"])

    @router.put("/{user_id}/reopen")
    async def reopen(user_id: str, request: Request) -> dict[str, str]:
        actor = await require_role("partner")(request)
        try: step_id = await service.reopen(actor, user_id)
        except PartnerNotLinked as error: raise HTTPException(400, "User not linked to a partner") from error
        except ManagedMilestoneNotFound as error: raise HTTPException(400, "No managed milestone found for this user") from error
        return {"message": "Milestone re-opened", "step_id": step_id}

    @router.put("/{user_id}/progress")
    async def update_progress(user_id: str, data: UserProgressUpdate, request: Request) -> dict[str, str]:
        actor = await require_role("partner")(request)
        try:
            await service.update_progress(actor, user_id, ProgressCommand(data.step_id, data.status, data.data or {}))
        except PartnerNotLinked as error: raise HTTPException(400, "User not linked to a partner") from error
        except WorkspaceCommandStepNotFound as error: raise HTTPException(404, "Step not found") from error
        except WorkspaceStepNotManaged as error: raise HTTPException(403, "This step is not managed by your partner organization") from error
        except WorkspaceUserNotFound as error: raise HTTPException(404, "User not found") from error
        return {"message": "User progress updated"}

    return router


def build_partner_workspace_detail_router(
    service: PartnerWorkspaceDetailService, require_role: Guard,
) -> APIRouter:
    router = APIRouter(prefix="/partner/users", tags=["partner"])

    @router.get("/{user_id}")
    async def detail(user_id: str, request: Request) -> dict[str, Any]:
        actor = await require_role("partner")(request)
        try: return await service.detail(actor, user_id)
        except PartnerNotLinked as error: raise HTTPException(400, "User not linked to a partner") from error
        except WorkspaceUserNotFound as error: raise HTTPException(404, "User not found") from error

    return router


def build_partner_workspace_read_router(
    service: PartnerWorkspaceReadService, require_role: Guard,
) -> APIRouter:
    router = APIRouter(prefix="/partner", tags=["partner"])

    async def actor(request: Request) -> Actor:
        return await require_role("partner")(request)

    @router.get("/submissions")
    async def submissions(request: Request) -> list[dict[str, Any]]:
        try: return await service.submissions(await actor(request))
        except PartnerNotLinked as error: raise HTTPException(400, "User not linked to a partner") from error

    @router.get("/other-users")
    async def other_users(request: Request) -> list[dict[str, Any]]:
        try: return await service.other_users(await actor(request))
        except PartnerNotLinked as error: raise HTTPException(400, "User not linked to a partner") from error

    return router
