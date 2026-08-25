"""Translate partner-selection domain failures into the public HTTP contract."""
from __future__ import annotations

from fastapi import HTTPException

from slices.partner_selection.domain import (
    EmptyPartnerSelection,
    InvalidSelectionStep,
    MultipleSelectionRequired,
    PartnerNotOffered,
    PartnerSelectionError,
    PartnerUnavailable,
    SelectionSurveyMismatch,
)


def partner_selection_http_exception(error: PartnerSelectionError) -> HTTPException:
    if isinstance(error, (InvalidSelectionStep, SelectionSurveyMismatch)):
        return HTTPException(status_code=400, detail="Submission step is invalid or belongs to another survey")
    if isinstance(error, MultipleSelectionRequired):
        return HTTPException(status_code=400, detail="Multiple partners require a multi-selection step")
    if isinstance(error, EmptyPartnerSelection):
        return HTTPException(status_code=422, detail="At least one partner must be selected")
    if isinstance(error, PartnerUnavailable):
        return HTTPException(status_code=404, detail="Partner not found or inactive")
    if isinstance(error, PartnerNotOffered):
        return HTTPException(status_code=400, detail="Partner is not offered in this selection step")
    raise TypeError(f"Unsupported partner-selection error: {type(error).__name__}")
