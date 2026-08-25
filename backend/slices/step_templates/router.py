"""FastAPI administration routes for reusable step templates."""
from __future__ import annotations
from collections.abc import Awaitable, Callable, Mapping
from typing import Any
from fastapi import APIRouter, Query, Request
from slices.step_templates.models import TemplateDraft
from slices.step_templates.service import StepTemplateService
from slices.step_templates.web import StepTemplateCreate, StepTemplateUpdate, step_template_http_error

Actor = Mapping[str, Any]
Guard = Callable[[str], Callable[[Request], Awaitable[Actor]]]
Audit = Callable[[object, object, str, str, object, Mapping[str, Any]], Awaitable[None]]
DefaultSurvey = Callable[[], Awaitable[Mapping[str, Any]]]

def build_step_templates_router(service: StepTemplateService, require_role: Guard,
                                audit: Audit, default_survey: DefaultSurvey) -> APIRouter:
    router = APIRouter(prefix="/admin", tags=["admin"])
    @router.get("/step-templates")
    async def templates(request: Request) -> list[dict[str, Any]]:
        await require_role("admin")(request); return await service.templates()
    @router.post("/step-templates")
    async def create(data: StepTemplateCreate, request: Request) -> dict[str, str]:
        actor = await require_role("admin")(request)
        template_id = await service.create(TemplateDraft(data.name, data.description or "", data.config))
        await audit(actor["_id"], actor["email"], "step_template_create", "step_template", template_id, {"name": data.name})
        return {"id": template_id, "message": "Template created"}
    @router.put("/step-templates/{template_id}")
    async def update(template_id: str, data: StepTemplateUpdate, request: Request) -> dict[str, str]:
        actor = await require_role("admin")(request); fields = await service.update(template_id, data.model_dump())
        await audit(actor["_id"], actor["email"], "step_template_update", "step_template", template_id, {"fields": fields})
        return {"message": "Template updated"}
    @router.delete("/step-templates/{template_id}")
    async def delete(template_id: str, request: Request) -> dict[str, str]:
        actor = await require_role("admin")(request)
        try: name = await service.delete(template_id)
        except Exception as error: raise step_template_http_error(error)
        await audit(actor["_id"], actor["email"], "step_template_delete", "step_template", template_id, {"name": name})
        return {"message": "Template deleted"}
    @router.post("/step-templates/from-step/{step_id}")
    async def from_step(step_id: str, request: Request, name: str = Query(...),
                        description: str = Query("")) -> dict[str, str]:
        actor = await require_role("admin")(request)
        try: template_id = await service.create_from_step(step_id, name, description)
        except Exception as error: raise step_template_http_error(error)
        await audit(actor["_id"], actor["email"], "step_template_create", "step_template", template_id,
                    {"from_step": step_id, "name": name})
        return {"id": template_id, "message": "Template saved from step"}
    @router.post("/step-templates/{template_id}/apply")
    async def apply(template_id: str, request: Request, order: int = Query(...),
                    survey_id: str | None = Query(None)) -> dict[str, str]:
        actor = await require_role("admin")(request)
        target = survey_id or str((await default_survey())["_id"])
        try: result = await service.apply(template_id, target, order, actor)
        except Exception as error: raise step_template_http_error(error)
        await audit(actor["_id"], actor["email"], "step_template_apply", "step", result.step_id,
                    {"template_id": template_id, "order": order})
        return {"id": result.step_id, "message": "Template applied as new step"}
    return router
