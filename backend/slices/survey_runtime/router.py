"""FastAPI read boundary for the user survey runtime."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from slices.survey_runtime.dashboard import SurveyDashboardService
from slices.survey_runtime.progress import MissingMultiUpload, MissingRequiredFields, MissingRequiredUploads
from slices.survey_runtime.progress_service import ProgressCommand, ProgressStepNotFound, SurveyProgressService
from slices.survey_runtime.web import UserProgressUpdate


CurrentUser = Callable[[Request], Awaitable[dict[str, Any]]]
Survey = Callable[[Mapping[str, Any], str | None], Awaitable[Mapping[str, Any]]]
Estimate = Callable[[str], Awaitable[Any]]
Visibility = Callable[[str], Awaitable[tuple[Any, Any, set[str], set[str]]]]
RoleGuard = Callable[..., Callable[[Request], Awaitable[Mapping[str, Any]]]]


def build_survey_estimate_router(estimate: Estimate, require_role: RoleGuard) -> APIRouter:
    """Expose another user's estimate only to administrative partner roles."""
    router = APIRouter(prefix="/users", tags=["steps"])

    @router.get("/{user_id}/estimated-completion")
    async def estimated_completion(user_id: str, request: Request) -> dict[str, Any]:
        await require_role("admin", "partner")(request)
        return {"estimated_completion": await estimate(user_id)}

    return router


def build_survey_runtime_read_router(
    service: SurveyDashboardService, current_user: CurrentUser,
    user_survey: Survey, estimate: Estimate, visibility: Visibility,
) -> APIRouter:
    router = APIRouter(prefix="/steps", tags=["steps"])

    async def context(request: Request, slug: str | None) -> tuple[dict[str, Any], str]:
        user = await current_user(request)
        survey = await user_survey(user, slug)
        return user, str(survey["_id"])

    @router.get("")
    async def steps(request: Request, survey_slug: str | None = Query(None)) -> list[dict[str, Any]]:
        _, survey_id = await context(request, survey_slug)
        return await service.steps(survey_id)

    @router.get("/progress")
    async def progress(request: Request, survey_slug: str | None = Query(None)) -> list[dict[str, Any]]:
        user, survey_id = await context(request, survey_slug)
        return await service.progress(str(user["_id"]), survey_id)

    @router.get("/all-data")
    async def all_data(request: Request, survey_slug: str | None = Query(None)) -> list[dict[str, Any]]:
        user, survey_id = await context(request, survey_slug)
        return await service.all_data(str(user["_id"]), survey_id)

    @router.get("/bootstrap")
    async def bootstrap(request: Request, survey_slug: str | None = Query(None)) -> dict[str, Any]:
        user, survey_id = await context(request, survey_slug)
        return await service.bootstrap(user, survey_id)

    @router.get("/history")
    async def history(request: Request) -> list[dict[str, Any]]:
        user = await current_user(request)
        return await service.history(str(user["_id"]))

    @router.get("/estimated-completion")
    async def estimated_completion(request: Request) -> dict[str, Any]:
        user = await current_user(request)
        return {"estimated_completion": await estimate(str(user["_id"]))}

    @router.get("/visibility")
    async def step_visibility(request: Request) -> dict[str, list[str]]:
        user = await current_user(request)
        _, _, hidden, blocked = await visibility(str(user["_id"]))
        return {"hidden_step_ids": list(hidden), "blocked_step_ids": list(blocked)}

    return router


def build_survey_progress_router(
    service: SurveyProgressService, current_user: CurrentUser,
) -> APIRouter:
    router = APIRouter(prefix="/steps", tags=["steps"])

    @router.put("/progress")
    async def update_progress(data: UserProgressUpdate, request: Request) -> dict[str, str]:
        user = await current_user(request)
        try:
            await service.update(user, ProgressCommand(data.step_id, data.status, data.data or {}))
        except ProgressStepNotFound as error:
            raise HTTPException(404, "Step not found") from error
        except MissingRequiredFields as error:
            raise HTTPException(400, f"Pflichtfelder fehlen: {', '.join(error.labels)}") from error
        except MissingRequiredUploads as error:
            raise HTTPException(400, f"Erforderliche Dokumente fehlen: {', '.join(error.document_types)}") from error
        except MissingMultiUpload as error:
            raise HTTPException(400, f"Mindestens ein Dokument für '{error.label}' ist erforderlich.") from error
        return {"message": "Progress updated"}

    return router
