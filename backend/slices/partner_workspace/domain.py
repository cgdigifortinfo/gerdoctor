"""Pure business rules for the partner user workspace."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from slices.partner_workspace.models import (
    WorkspaceAction,
    WorkspaceProgress,
    WorkspaceRevision,
    WorkspaceStep,
    WorkspaceUpload,
)


class InvalidWorkspaceAction(ValueError):
    pass


class RejectionReasonRequired(ValueError):
    pass


def validate_workspace_action(action: str, reason: str | None) -> WorkspaceAction:
    try:
        parsed = WorkspaceAction(action)
    except ValueError as exc:
        raise InvalidWorkspaceAction(action) from exc
    if parsed is WorkspaceAction.REJECT and not (reason or "").strip():
        raise RejectionReasonRequired from None
    return parsed


def merge_progress_data(
    existing: Mapping[str, Any], incoming: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {**existing, **(incoming or {})}


def new_partner_uploads(
    existing: Mapping[str, Any], merged: Mapping[str, Any],
) -> tuple[WorkspaceUpload, ...]:
    old_ids = {
        str(item.get("file_id"))
        for item in _upload_documents(existing)
        if item.get("file_id")
    }
    return tuple(
        WorkspaceUpload(
            file_id=str(item.get("file_id")),
            filename=str(item.get("filename") or ""),
            document=item,
        )
        for item in _upload_documents(merged)
        if item.get("file_id") and str(item.get("file_id")) not in old_ids
    )


def _upload_documents(data: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    uploads = data.get("partner_uploads")
    if not isinstance(uploads, list):
        return ()
    return tuple(item for item in uploads if isinstance(item, Mapping))


def adjacent_visible_step(
    steps: Iterable[WorkspaceStep], current: WorkspaceStep, hidden_step_ids: Iterable[str], *, forward: bool,
) -> WorkspaceStep | None:
    hidden = frozenset(hidden_step_ids)
    candidates = tuple(
        step for step in steps
        if step.id not in hidden and (step.order > current.order if forward else step.order < current.order)
    )
    if not candidates:
        return None
    return min(candidates, key=lambda step: step.order) if forward else max(candidates, key=lambda step: step.order)


def partner_selection_step_id(steps: Iterable[WorkspaceStep], partner_tags: Iterable[str]) -> str | None:
    tags = frozenset(partner_tags)
    return next((
        step.id for step in steps
        if step.step_type in {"partner_selection", "partner_multiselection"} and step.filter_tag in tags
    ), None)


def revision_is_visible(
    revision: WorkspaceRevision, managed_step_ids: Iterable[str], partner_id: str, partner_name: str,
) -> bool:
    return (
        revision.step_id in frozenset(managed_step_ids)
        or revision.changed_by_partner_id == partner_id
        or _contains_value(revision.data, partner_id)
        or bool(partner_name and _contains_value(revision.data, partner_name))
    )


def _contains_value(value: object, expected: str) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_value(item, expected) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_value(item, expected) for item in value)
    return value == expected


def sanitize_progress(
    progress: Iterable[WorkspaceProgress], steps: Iterable[WorkspaceStep], partner_id: str,
    revision_markers: Mapping[tuple[str, int | None], Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    step_by_id = {step.id: step for step in steps}
    marker_keys = (
        "current_step_version", "configuration_changed", "step_deleted",
        "step_snapshot", "removed_field_names",
    )
    result = []
    for row in progress:
        document = dict(row.document)
        step = step_by_id.get(row.step_id)
        selected_partner = row.data.get("selected_partner_id")
        if (
            step and step.step_type in {"partner_selection", "partner_multiselection"}
            and selected_partner and selected_partner != partner_id
        ):
            document["data"] = {}
        marker = revision_markers.get((row.step_id, row.revision), {})
        document.update({key: marker.get(key) for key in marker_keys})
        result.append(document)
    return tuple(result)
