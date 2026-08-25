"""HTTP request models owned by the partner-selection slice."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PartnerSubmissionCreate(BaseModel):
    partner_id: str
    data: dict[str, Any] = Field(default_factory=dict)


class MultiPartnerSubmission(BaseModel):
    partner_ids: list[str]
    data: dict[str, Any] = Field(default_factory=dict)
