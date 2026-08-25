"""FastAPI routes for survey administration and public survey discovery."""
from __future__ import annotations
from collections.abc import Awaitable, Callable, Mapping
from typing import Any
from fastapi import APIRouter, Request
from slices.survey_administration.domain import normalized_slug, survey_view
from slices.survey_administration.models import SurveyDraft
from slices.survey_administration.service import SurveyAdministrationService
from slices.survey_administration.web import SurveyCreate, SurveyUpdate, survey_http_error

Actor = Mapping[str, Any]
RoleGuard = Callable[[str], Callable[[Request], Awaitable[Actor]]]
Audit = Callable[[object, object, str, str, object, Mapping[str, Any]], Awaitable[None]]

def build_survey_routers(service: SurveyAdministrationService, require_role: RoleGuard,
                         audit: Audit) -> tuple[APIRouter, APIRouter]:
    admin = APIRouter(prefix="/admin", tags=["admin"])
    public = APIRouter(prefix="/surveys", tags=["surveys"])

    @public.get("/public")
    async def list_public_surveys() -> list[dict[str, Any]]:
        return [item for item in await service.list_surveys() if item["is_active"]]

    @public.get("/slug/{slug}")
    async def get_public_survey(slug: str) -> dict[str, Any]:
        try: return survey_view(await service.by_slug(slug))
        except Exception as error: raise survey_http_error(error)

    @admin.get("/surveys")
    async def list_surveys(request: Request) -> list[dict[str, Any]]:
        await require_role("admin")(request); return await service.list_surveys()

    @admin.post("/surveys")
    async def create_survey(data: SurveyCreate, request: Request) -> dict[str, str]:
        actor = await require_role("admin")(request)
        draft = SurveyDraft(data.name, data.slug, data.description or "", data.audience or "",
                            data.is_active, data.is_default, data.theme)
        try: survey_id = await service.create(draft)
        except Exception as error: raise survey_http_error(error)
        await audit(actor["_id"], actor["email"], "survey_create", "survey", survey_id,
                    {"name": data.name, "slug": normalized_slug(data.slug)})
        return {"id": survey_id, "message": "Survey created"}

    @admin.put("/surveys/{survey_id}")
    async def update_survey(survey_id: str, data: SurveyUpdate, request: Request) -> dict[str, str]:
        actor = await require_role("admin")(request)
        try: fields = await service.update(survey_id, data.model_dump())
        except Exception as error: raise survey_http_error(error)
        await audit(actor["_id"], actor["email"], "survey_update", "survey", survey_id,
                    {"fields_changed": fields})
        return {"message": "Survey updated"}
    return admin, public
