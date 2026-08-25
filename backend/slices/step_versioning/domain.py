"""Deterministic rules used by Step and answer versioning."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from collections.abc import Iterator, Mapping, Sequence
from typing import Any

from slices.step_versioning.models import ProgressRevisionPlan

def step_snapshot(step: Mapping[str, Any]) -> dict[str, Any]:
    """Return configuration only, excluding mutable version metadata."""
    excluded = {"current_version", "deleted_at", "deleted_by", "updated_at"}
    return {key: value for key, value in step.items() if key not in excluded}


def snapshot_hash(snapshot: Mapping[str, Any]) -> str:
    """Hash a snapshot independently of dictionary insertion order."""
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)  # pragma: no mutate - None is equivalent to False
    return hashlib.sha256(canonical.encode()).hexdigest()


def file_references(value: Any, path: str = "data") -> Iterator[tuple[str, Mapping[str, Any]]]:
    """Yield every nested upload object together with its stable data path."""
    if isinstance(value, Mapping):
        if value.get("file_id"):
            yield path, value
        for key, item in value.items():
            yield from file_references(item, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, item in enumerate(value):
            yield from file_references(item, f"{path}[{index}]")


def step_version_document(
    step_id: str, step: Mapping[str, Any], version: int, actor: Mapping[str, Any] | None,
    change_type: str, created_at: str,
) -> dict[str, Any]:
    snapshot = step_snapshot(step)
    return {
        "step_id": step_id,
        "version": version,
        "snapshot": snapshot,
        "snapshot_hash": snapshot_hash(snapshot),
        "change_type": change_type,
        "created_at": created_at,
        "created_by": dict(actor or {}),
    }


def progress_revision_plan(
    *, existing: Mapping[str, Any] | None, step: Mapping[str, Any], user_id: str,
    status: str, data: Mapping[str, Any] | None, step_version: int,
    revision: int, actor: Mapping[str, Any] | None, change_type: str,
    changed_at: str, extra_fields: Mapping[str, Any] | None = None,
    unset_fields: Sequence[str] | None = None,
) -> ProgressRevisionPlan:
    previous = existing or {}
    current: dict[str, Any] = {
        "user_id": user_id,
        "step_id": str(step.get("_id") or step.get("id")),
        "survey_id": step.get("survey_id"),
        "step_order": step.get("order", 0),
        "status": status,
        "data": deepcopy(data if data is not None else previous.get("data") or {}),
        "step_version": step_version,
        "revision": revision,
        "started_at": previous.get("started_at") or changed_at,
        "updated_at": changed_at,
        **dict(extra_fields or {}),
    }
    removed = tuple(unset_fields or ())
    for field in removed:
        current.pop(field, None)
    revision_document = {
        **current,
        "created_at": changed_at,
        "change_type": change_type,
        "changed_by": dict(actor or {}),
    }
    return ProgressRevisionPlan(current, revision_document, removed)


def document_binding(
    revision: Mapping[str, Any], path: str, entry: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "file_id": str(entry["file_id"]),
        "user_id": revision["user_id"],
        "step_id": revision["step_id"],
        "step_version": revision["step_version"],
        "progress_revision": revision["revision"],
        "field_path": path,
        "document_type": entry.get("document_type"),
        "filename": entry.get("filename") or entry.get("name"),
        "uploaded_by": entry.get("uploaded_by") or ("partner" if "partner_uploads" in path else "user"),
        "partner_id": entry.get("partner_id"),
        "created_at": revision["created_at"],
        "historical_protected": True,
    }


def answer_history_item(
    row: Mapping[str, Any], live: Mapping[str, Any] | None,
    historical: Mapping[str, Any] | None,
) -> dict[str, Any]:
    version_document = historical or {}
    snapshot = version_document.get("snapshot") or {}
    live_step = live or {}
    current_version = int(live_step.get("current_version") or row.get("step_version") or 1)
    old_names = {field.get("name") for field in snapshot.get("fields", []) if field.get("name")}
    current_names = {field.get("name") for field in live_step.get("fields", []) if field.get("name")}
    content_changed = bool(live) and snapshot_hash(step_snapshot(live_step)) != version_document.get("snapshot_hash")
    return {
        **row,
        "step_title": snapshot.get("title") or live_step.get("title") or "Gelöschter Schritt",
        "current_step_version": current_version,
        "configuration_changed": (
            current_version != row.get("step_version") or content_changed or bool(live_step.get("is_deleted"))
        ),
        "step_deleted": bool(live_step.get("is_deleted")) or live is None,
        "step_snapshot": snapshot,
        "removed_field_names": sorted(old_names - current_names),
    }
