"""Document-workflow persistence port."""
from __future__ import annotations

from typing import Protocol

from slices.document_workflow.models import DocumentWorkflowContext


class DocumentWorkflowRepository(Protocol):
    async def load(self, user_id: str, survey_id: str | None) -> DocumentWorkflowContext: ...
