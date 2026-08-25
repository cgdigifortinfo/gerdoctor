"""HTTP models for survey progress commands."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class UserProgressUpdate(BaseModel):
    step_id: str
    status: str
    data: dict[str, Any] | None = None
