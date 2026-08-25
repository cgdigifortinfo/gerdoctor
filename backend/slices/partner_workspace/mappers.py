"""Boundary mappers for partner workspace database documents."""
from __future__ import annotations

from typing import Any, Mapping

from slices.partner_workspace.models import (
    WorkspaceProgress,
    WorkspaceRevision,
    WorkspaceStep,
    WorkspaceUser,
)


def workspace_user_from_document(document: Mapping[str, Any]) -> WorkspaceUser:
    survey_id = document.get("survey_id")
    preferences = document.get("notification_preferences")
    return WorkspaceUser(
        id=str(document.get("_id") or document.get("id") or ""),
        name=str(document.get("name") or ""),
        email=str(document.get("email") or ""),
        survey_id=str(survey_id) if survey_id else None,
        notification_preferences=preferences if isinstance(preferences, Mapping) else {},
    )


def workspace_step_from_document(document: Mapping[str, Any]) -> WorkspaceStep:
    return WorkspaceStep(
        id=str(document.get("_id") or document.get("id") or ""),
        order=float(document.get("order") or 0),
        title=str(document.get("title") or ""),
        step_type=str(document.get("step_type") or ""),
        filter_tag=str(document.get("filter_tag") or ""),
        description=str(document.get("description") or ""),
        document={key: value for key, value in document.items() if key != "_id"},
    )


def workspace_progress_from_document(document: Mapping[str, Any]) -> WorkspaceProgress:
    revision = document.get("revision")
    data = document.get("data")
    return WorkspaceProgress(
        step_id=str(document.get("step_id") or ""),
        status=str(document.get("status") or "pending"),
        revision=int(revision) if isinstance(revision, int) else None,
        data=data if isinstance(data, Mapping) else {},
        document=dict(document),
    )


def workspace_revision_from_document(document: Mapping[str, Any]) -> WorkspaceRevision:
    changed_by = document.get("changed_by")
    data = document.get("data")
    revision = document.get("revision")
    return WorkspaceRevision(
        step_id=str(document.get("step_id") or ""),
        revision=int(revision) if isinstance(revision, int) else None,
        changed_by_partner_id=str(changed_by.get("partner_id") or "") if isinstance(changed_by, Mapping) else "",
        data=data if isinstance(data, Mapping) else {},
    )
