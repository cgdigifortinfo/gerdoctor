"""HTTP request models and error mapping for step templates."""
from __future__ import annotations
from typing import Any
from fastapi import HTTPException
from pydantic import BaseModel
from slices.step_templates.service import SourceStepNotFound, TemplateNotFound

class StepTemplateCreate(BaseModel):
    name: str
    description: str | None = ""
    config: dict[str, Any]
class StepTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None
def step_template_http_error(error: Exception) -> HTTPException:
    if isinstance(error, TemplateNotFound): return HTTPException(404, "Template not found")
    if isinstance(error, SourceStepNotFound): return HTTPException(404, "Step not found")
    return HTTPException(500, "Step template operation failed")
