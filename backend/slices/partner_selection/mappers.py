"""Database boundary mappers for partner selection."""
from __future__ import annotations

from typing import Any, Mapping

from slices.partner_selection.models import (
    SelectablePartner,
    SelectionKind,
    SelectionStep,
    SelectionUser,
)


def selection_user_from_document(document: Mapping[str, Any]) -> SelectionUser:
    survey_id = document.get("survey_id")
    return SelectionUser(
        id=str(document.get("_id") or document.get("id") or ""),
        survey_id=str(survey_id) if survey_id else None,
    )


def selection_step_from_document(document: Mapping[str, Any]) -> SelectionStep | None:
    raw_kind = str(document.get("step_type") or "")  # pragma: no mutate - every fallback is invalid
    try:
        kind = SelectionKind(raw_kind)
    except ValueError:
        return None
    survey_id = document.get("survey_id")
    return SelectionStep(
        id=str(document.get("_id") or document.get("id") or ""),
        kind=kind,
        survey_id=str(survey_id) if survey_id else None,
        filter_tag=str(document.get("filter_tag") or ""),
        document=dict(document),
    )


def selectable_partner_from_document(document: Mapping[str, Any]) -> SelectablePartner:
    raw_tags = document.get("tags")
    tags = raw_tags if isinstance(raw_tags, list) else []
    return SelectablePartner(
        id=str(document.get("_id") or document.get("id") or ""),
        name=str(document.get("name") or ""),
        tags=frozenset(str(tag) for tag in tags),
        active=document.get("is_active") is True,
        document=dict(document),
    )
