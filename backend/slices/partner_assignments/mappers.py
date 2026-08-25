"""Mongo/API mapping for partner assignment domain values."""
from __future__ import annotations

from typing import Any, Mapping

from slices.partner_assignments.models import FlowStep, StepKind, StepProgress


PARTNER_STEP_KINDS = {
    StepKind.PARTNER_SELECTION.value: StepKind.PARTNER_SELECTION,
    StepKind.PARTNER_MULTI_SELECTION.value: StepKind.PARTNER_MULTI_SELECTION,
    StepKind.MILESTONE.value: StepKind.MILESTONE,
    StepKind.DECISION.value: StepKind.DECISION,
}


def flow_step_from_document(document: Mapping[str, Any]) -> FlowStep:
    return FlowStep(
        id=str(document.get("id") or document.get("_id") or ""),
        order=float(document.get("order") or 0),
        kind=PARTNER_STEP_KINDS.get(str(document.get("step_type")), StepKind.OTHER),
    )


def progress_from_document(document: Mapping[str, Any]) -> StepProgress:
    data = document.get("data") or {}
    selected = {str(value) for value in data.get("selected_partner_ids") or []}
    if data.get("selected_partner_id"):
        selected.add(str(data["selected_partner_id"]))
    return StepProgress(
        step_id=str(document.get("step_id") or ""),
        status=str(document.get("status") or "pending"),
        selected_partner_ids=frozenset(selected),
        selected_partner_name=str(data.get("selected_partner_name") or ""),
        completed_at=document.get("completed_at"),
    )
