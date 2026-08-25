"""Map persistence documents into document-workflow values."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from slices.document_workflow.models import DocumentWorkflowContext, WorkflowProgress, WorkflowStep


def workflow_step_from_document(document: Mapping[str, Any]) -> WorkflowStep:
    return WorkflowStep(
        id=str(document.get("_id") or document.get("id") or ""),
        order=float(document.get("order") or 0),
        kind=str(document.get("step_type") or ""),
        fields=tuple(document.get("fields") or ()),
        conditions=tuple(document.get("conditions") or ()),
        document=document,
    )


def workflow_progress_from_document(document: Mapping[str, Any]) -> WorkflowProgress:
    return WorkflowProgress(
        step_id=str(document.get("step_id") or ""),
        status=str(document.get("status") or "pending"),
        data=document.get("data") or {},
    )


def document_workflow_context(
    steps: Sequence[Mapping[str, Any]], progress: Sequence[Mapping[str, Any]],
) -> DocumentWorkflowContext:
    return DocumentWorkflowContext(
        tuple(workflow_step_from_document(step) for step in steps),
        tuple(workflow_progress_from_document(row) for row in progress),
    )
