"""FastAPI routes for administrative step configuration."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from slices.step_configuration.administration import (
    StepAdministrationInvalidId,
    StepAdministrationNotFound,
    StepAdministrationService,
)
from slices.step_configuration.service import StepConfigurationNotFound, StepConfigurationService
from slices.step_configuration.web import step_configuration_http_error
from slices.step_configuration.web_models import (
    StepCreate,
    StepLayoutBulk,
    StepReorder,
    StepResponse,
    StepUpdate,
)


Actor = Mapping[str, Any]
Guard = Callable[[str], Callable[[Request], Awaitable[Actor]]]
Audit = Callable[[object, object, str, str, object, Mapping[str, Any]], Awaitable[None]]
SurveyLookup = Callable[[str | None], Awaitable[Mapping[str, Any]]]
Payload = Callable[[Mapping[str, Any]], dict[str, Any]]


def build_step_configuration_router(
    commands: StepConfigurationService,
    administration: StepAdministrationService,
    require_role: Guard,
    survey_by_slug: SurveyLookup,
    default_survey: Callable[[], Awaitable[Mapping[str, Any]]],
    payload: Payload,
    audit: Audit,
) -> APIRouter:
    router = APIRouter(prefix="/admin/steps", tags=["admin"])

    def actor(document: Actor) -> dict[str, Any]:
        return {"id": str(document["_id"]), "email": document["email"], "role": "admin"}

    @router.get("", response_model=list[StepResponse])
    async def steps(
        request: Request,
        survey_id: str | None = Query(None),
        survey_slug: str | None = Query(None),
        include_deleted: bool = Query(False),
    ) -> list[dict[str, Any]]:
        await require_role("admin")(request)
        selected_survey_id = survey_id
        if survey_slug:
            selected_survey_id = str((await survey_by_slug(survey_slug))["_id"])
        return [payload(step) for step in await administration.steps(
            selected_survey_id, include_deleted,
        )]

    @router.post("")
    async def create(data: StepCreate, request: Request) -> dict[str, str]:
        admin = await require_role("admin")(request)
        survey_id = data.survey_id or str((await default_survey())["_id"])
        step_id = await commands.create(data.model_dump(), survey_id, actor(admin))
        await audit(admin["_id"], admin["email"], "step_create", "step", step_id, {
            "title": data.title, "before_version": None, "after_version": 1,
        })
        return {"id": step_id, "message": "Step created"}

    @router.put("/reorder")
    async def reorder(data: StepReorder, request: Request) -> dict[str, str]:
        admin = await require_role("admin")(request)
        changes = await administration.reorder(data.step_ids, data.survey_id, actor(admin))
        await audit(admin["_id"], admin["email"], "steps_reorder", "step", "", {
            "new_order": data.step_ids, "version_changes": changes,
        })
        return {"message": "Steps reordered"}

    @router.put("/layout-bulk")
    async def layout(data: StepLayoutBulk, request: Request) -> dict[str, Any]:
        admin = await require_role("admin")(request)
        positions = {
            step_id: position.model_dump() for step_id, position in data.positions.items()
        }
        changes = await administration.save_layout(positions, actor(admin))
        await audit(admin["_id"], admin["email"], "steps_layout_saved", "step", "", {
            "count": len(changes), "version_changes": changes,
        })
        return {"message": "Layout saved", "updated": len(changes)}

    @router.put("/{step_id}")
    async def update(step_id: str, data: StepUpdate, request: Request) -> dict[str, Any]:
        admin = await require_role("admin")(request)
        try:
            before, after = await commands.update(
                step_id, data.model_dump(), frozenset(data.model_fields_set), actor(admin),
            )
        except StepConfigurationNotFound as error:
            raise step_configuration_http_error(error)
        changed = [key for key, value in data.model_dump().items() if value is not None]
        await audit(admin["_id"], admin["email"], "step_update", "step", step_id, {
            "fields_changed": changed, "before_version": before, "after_version": after,
        })
        return {"message": "Step updated", "before_version": before, "after_version": after}

    @router.get("/{step_id}/versions")
    async def versions(step_id: str, request: Request) -> list[dict[str, Any]]:
        await require_role("admin")(request)
        try:
            return await administration.versions(step_id)
        except StepAdministrationInvalidId as error:
            raise HTTPException(400, "Invalid step id") from error
        except StepAdministrationNotFound as error:
            raise HTTPException(404, "Step not found") from error

    @router.delete("/{step_id}")
    async def archive(step_id: str, request: Request) -> dict[str, Any]:
        admin = await require_role("admin")(request)
        try:
            step, before, after = await administration.archive(step_id, actor(admin))
        except StepAdministrationNotFound as error:
            raise HTTPException(404, "Step not found") from error
        if before is None:
            return {"message": "Step already archived"}
        await audit(admin["_id"], admin["email"], "step_delete", "step", step_id, {
            "title": step["title"], "before_version": before, "after_version": after,
            "soft_delete": True,
        })
        return {"message": "Step archived", "before_version": before, "after_version": after}

    return router
