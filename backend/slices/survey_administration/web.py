"""Survey HTTP request models and safe error mapping."""
from __future__ import annotations
from typing import Any
from fastapi import HTTPException
from pydantic import BaseModel
from slices.survey_administration.service import DuplicateSurveySlug, SurveyNotFound, SurveySlugRequired

class SurveyCreate(BaseModel):
    name: str; slug: str; description: str | None = ""; audience: str | None = ""
    is_active: bool = True; is_default: bool = False; theme: dict[str, Any] | None = None
class SurveyUpdate(BaseModel):
    name: str | None = None; slug: str | None = None; description: str | None = None
    audience: str | None = None; is_active: bool | None = None; is_default: bool | None = None
    theme: dict[str, Any] | None = None
def survey_http_error(error: Exception) -> HTTPException:
    if isinstance(error, SurveyNotFound): return HTTPException(404, "Survey not found")
    if isinstance(error, SurveySlugRequired): return HTTPException(400, "Slug is required")
    if isinstance(error, DuplicateSurveySlug): return HTTPException(400, "Survey slug already exists")
    return HTTPException(500, "Survey operation failed")
