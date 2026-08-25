"""Validation rules for survey progress writes."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class MissingRequiredFields(ValueError):
    def __init__(self, labels: list[str]) -> None:
        self.labels = labels


class MissingRequiredUploads(ValueError):
    def __init__(self, document_types: list[str]) -> None:
        self.document_types = document_types


class MissingMultiUpload(ValueError):
    def __init__(self, label: str) -> None:
        self.label = label


def validate_completion(step: Mapping[str, Any], data: Mapping[str, Any],
                        content_field_types: frozenset[str]) -> None:
    required = list(dict.fromkeys([
        *(step.get("required_fields") or []),
        *[
            field.get("name") for field in step.get("fields", [])
            if field.get("required") and field.get("name")
            and field.get("field_type") not in content_field_types | {"multiupload"}
        ],
    ]))
    missing = [name for name in required if not data.get(name)
               or isinstance(data.get(name), str) and not str(data[name]).strip()]
    if missing:
        labels = {field["name"]: field.get("label", field["name"])
                  for field in step.get("fields", []) if field.get("name")}
        raise MissingRequiredFields([str(labels.get(name, name)) for name in missing])
    uploaded_types = {
        str(entry["document_type"])
        for field in step.get("fields", []) if field.get("field_type") == "multiupload"
        for entry in data.get(field.get("name"), []) or []
        if isinstance(entry, dict) and entry.get("file_id") and entry.get("document_type")
    }
    missing_uploads = [name for name in step.get("required_uploads", [])
                       if name not in uploaded_types]
    if missing_uploads:
        raise MissingRequiredUploads(missing_uploads)
    for field in step.get("fields", []):
        if field.get("field_type") != "multiupload" or not field.get("required"):
            continue
        entries = data.get(field.get("name")) or []
        if not isinstance(entries, list) or not any(
            isinstance(entry, dict) and entry.get("file_id") for entry in entries
        ):
            raise MissingMultiUpload(str(field.get("label") or field.get("name")))
