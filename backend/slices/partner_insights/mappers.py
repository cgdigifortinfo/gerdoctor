"""Mapping of persisted partner analytics data into domain values."""
from __future__ import annotations

from typing import Any, Mapping

from slices.partner_insights.models import InsightPartner, InsightProfile, InsightSubmission


def insight_partner_from_document(document: Mapping[str, Any] | None) -> InsightPartner:
    document = document or {}
    awaiting = (
        document.get("registration_status") != "active"
        or document.get("is_active") is not True
        or not document.get("survey_ids")
    )
    return InsightPartner(
        id=str(document.get("id") or document.get("_id") or ""),
        name=str(document.get("name") or ""),
        awaiting_assignment=awaiting,
        linked_user_ids=frozenset(str(value) for value in document.get("linked_user_ids") or []),
    )


def insight_submission_from_document(document: Mapping[str, Any]) -> InsightSubmission:
    return InsightSubmission(
        user_id=str(document.get("user_id") or ""),
        service_step_id=str(document.get("step_id") or ""),
        submitted_at=str(document.get("created_at") or document.get("submitted_at") or ""),
    )


def insight_profile_from_document(document: Mapping[str, Any]) -> InsightProfile:
    return InsightProfile(
        specialty=str(
            document.get("fachrichtung_gewuenscht")
            or document.get("fachrichtung_praktiziert")
            or document.get("field_of_study")
            or "Unbekannt"
        ),
        state=str(document.get("anerkennungsverfahren_bundesland") or "Unbekannt"),
    )
