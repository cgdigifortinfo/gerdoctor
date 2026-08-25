"""Partner workspace HTTP models."""
from typing import Any
from pydantic import BaseModel


class PartnerSelfUpdate(BaseModel):
    description: str | None = None
    tags: list[str] | None = None


class PartnerStepAction(BaseModel):
    action: str
    reason: str | None = None
    data: dict[str, Any] | None = None
