"""Boundary mapping from persistence documents to survey runtime values."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from slices.survey_runtime.models import RuntimeProgress, RuntimeStep, SurveyRuntimeContext


def runtime_step_from_document(document: Mapping[str, Any]) -> RuntimeStep:
    return RuntimeStep(
        id=str(document.get("_id", "")),
        order=float(document.get("order", 0)),
        conditions=tuple(document.get("conditions") or ()),
        duration_value=int(document.get("duration_value") or 0),
        duration_unit=str(document.get("duration_unit") or "days"),
        step_type=str(document.get("step_type") or ""),
        document=document,
    )


def runtime_progress_from_document(document: Mapping[str, Any]) -> RuntimeProgress:
    completed_at = document.get("completed_at")
    return RuntimeProgress(
        step_id=str(document.get("step_id", "")),
        status=str(document.get("status") or "pending"),
        data=document.get("data") or {},
        completed_at=str(completed_at) if completed_at else None,
    )


def runtime_context_from_documents(
    steps: Sequence[Mapping[str, Any]], progress: Sequence[Mapping[str, Any]],
) -> SurveyRuntimeContext:
    return SurveyRuntimeContext(
        steps=tuple(runtime_step_from_document(step) for step in steps),
        progress=tuple(runtime_progress_from_document(row) for row in progress),
    )
