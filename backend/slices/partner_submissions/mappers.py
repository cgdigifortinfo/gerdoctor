"""Adapters from persisted partner-submission documents to domain values."""
from __future__ import annotations

from typing import Any, Mapping

from slices.partner_submissions.models import (
    PartnerSubmission,
    SubmissionProgress,
    SubmissionStep,
    SubmissionStepKind,
)


STEP_KINDS = {
    SubmissionStepKind.MILESTONE.value: SubmissionStepKind.MILESTONE,
    SubmissionStepKind.DECISION.value: SubmissionStepKind.DECISION,
}


def submission_from_document(document: Mapping[str, Any]) -> PartnerSubmission:
    return PartnerSubmission(
        user_id=str(document.get("user_id") or ""),
        service_step_id=str(document.get("step_id") or ""),
    )


def submission_step_from_document(document: Mapping[str, Any]) -> SubmissionStep:
    return SubmissionStep(
        id=str(document.get("id") or document.get("_id") or ""),
        order=float(document.get("order") or 0),
        title=str(document.get("title") or ""),
        kind=STEP_KINDS.get(str(document.get("step_type")), SubmissionStepKind.OTHER),
    )


def submission_progress_from_document(document: Mapping[str, Any]) -> SubmissionProgress:
    return SubmissionProgress(
        step_id=str(document.get("step_id") or ""),
        status=str(document.get("status") or "pending"),
        completed_at=document.get("completed_at"),
    )
