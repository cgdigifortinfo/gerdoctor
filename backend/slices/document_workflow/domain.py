"""Pure rules for decision/upload/partner/document workflow blocks."""
from __future__ import annotations

from typing import Any, Mapping

from slices.document_workflow.models import (
    DocumentWorkflowContext, WorkflowDocument, WorkflowStep, WorkflowStepState,
)
from slices.survey_runtime.domain import evaluate_condition


UPLOAD_FIELD_KINDS = frozenset({"file", "upload", "multiupload"})
PARTNER_STEP_KINDS = frozenset({"partner_selection", "partner_multiselection"})


def _has_upload_field(step: WorkflowStep) -> bool:
    return any(field.get("field_type") in UPLOAD_FIELD_KINDS for field in step.fields)


def _documents(context: DocumentWorkflowContext, sources: tuple[WorkflowStep, ...]) -> tuple[WorkflowDocument, ...]:
    progress = {row.step_id: row for row in context.progress}
    result: list[WorkflowDocument] = []
    seen: set[str] = set()
    for source in sources:
        data = progress[source.id].data if source.id in progress else {}
        for field_name, value in data.items():
            if not isinstance(value, list):
                continue
            for entry in value:
                if not isinstance(entry, dict) or not entry.get("file_id"):
                    continue
                file_id = str(entry["file_id"])
                if file_id in seen:
                    continue
                seen.add(file_id)
                result.append(WorkflowDocument(
                    file_id=file_id,
                    filename=str(entry.get("filename") or "Dokument"),
                    document_type=str(entry.get("document_type") or "Dokument"),
                    uploaded_by=str(entry.get("uploaded_by") or ("partner" if field_name == "partner_uploads" else "user")),
                ))
    return tuple(result)


def resolve_document_workflow(context: DocumentWorkflowContext) -> dict[str, WorkflowStepState]:
    ordered = tuple(sorted(context.steps, key=lambda step: step.order))
    progress = {row.step_id: row for row in context.progress}
    order_state: dict[float, Mapping[str, Any]] = {
        step.order: {
            "data": progress[step.id].data if step.id in progress else {},
            "status": progress[step.id].status if step.id in progress else "pending",
        }
        for step in ordered
    }
    state: dict[str, WorkflowStepState] = {}
    decision: WorkflowStep | None = None  # pragma: no mutate - only identity comparison is observable
    branches: list[WorkflowStep] = []  # pragma: no mutate - always reset before a decision block is evaluated
    for step in ordered:
        if step.kind == "decision":
            decision, branches = step, []
            continue
        if decision is None:
            continue
        if step.kind != "milestone":
            branches.append(step)
            continue
        if any(_has_upload_field(branch) for branch in branches) and any(
            branch.kind in PARTNER_STEP_KINDS for branch in branches
        ):
            for candidate in (decision, *branches):
                candidate_locked = any(
                    rule.get("action") == "read_only" and evaluate_condition(rule, order_state)
                    for rule in candidate.conditions
                )
                state[candidate.id] = WorkflowStepState(read_only=candidate_locked)
            documents = _documents(context, (*branches, step))
            state[step.id] = WorkflowStepState(
                documents=documents,
                documents_pending=not bool(documents),
                document_workflow=True,
            )
        decision, branches = None, []
    return state
