"""Canonical normalization and relation rules for configurable survey steps."""
from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Iterator, Mapping, Sequence

from slices.step_configuration.models import StepConfigurationChange, StepRelationIssue


FORM_SCHEMA_VERSION = 1
CONTENT_FIELD_TYPES = frozenset({"heading", "paragraph", "html", "image", "divider"})
CHOICE_FIELD_TYPES = frozenset({"select", "selectbox", "radio", "multiselect", "decision"})
UPLOAD_FIELD_TYPES = frozenset({"file", "upload", "multiupload"})
SUPPORTED_FIELD_TYPES = frozenset({
    "text", "email", "phone", "number", "textarea", "date", "time", "checkbox",
    *CHOICE_FIELD_TYPES, *UPLOAD_FIELD_TYPES, *CONTENT_FIELD_TYPES,
})
SYSTEM_FIELDS = frozenset({"status", "partner_uploads"})


def _slug(value: str, fallback: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]+", "_", value.strip().lower())
    return normalized.strip("_") or fallback  # pragma: no mutate - normalized alphabet cannot contain mutation sentinels


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        parsed = default
    return max(minimum, min(parsed, maximum))


def normalize_field(field: Mapping[str, Any], index: int = 0) -> dict[str, Any]:
    result = deepcopy(dict(field))
    field_type = str(result.get("field_type") or "text").strip().lower()  # pragma: no mutate - fallback casing normalizes identically
    if field_type not in SUPPORTED_FIELD_TYPES:
        field_type = "text"
    result["field_type"] = field_type
    result["name"] = _slug(
        str(result.get("name") or result.get("label") or ""), f"{field_type}_{index + 1}",
    )
    result["id"] = str(result.get("id") or result["name"])
    result["label"] = str(result.get("label") or result.get("content") or result["name"])
    result["required"] = bool(result.get("required", False)) if field_type not in CONTENT_FIELD_TYPES else False  # pragma: no mutate - missing falsy defaults are equivalent
    width = result.get("width")
    result["width"] = width if width in {"half", "third"} else "full"
    result["help_text"] = str(result.get("help_text") or "")
    if field_type in CHOICE_FIELD_TYPES or field_type == "multiupload":
        result["options"] = list(result.get("options") or [])
    if field_type == "textarea":
        result["rows"] = _bounded_int(result.get("rows") or 4, 4, 2, 20)
    if field_type in UPLOAD_FIELD_TYPES:
        result["accept"] = str(result.get("accept") or ".pdf,.png,.jpg,.jpeg,.doc,.docx")
        result["multiple"] = bool(result.get("multiple", field_type == "multiupload"))
    if field_type == "heading":
        result["heading_level"] = _bounded_int(result.get("heading_level") or 2, 2, 2, 4)
    if field_type in {"heading", "paragraph", "html"}:
        result["content"] = str(result.get("content") or result["label"])
    if field_type == "image":
        result["image_url"] = str(result.get("image_url") or "")
        result["alt_text"] = str(result.get("alt_text") or result["label"])
        result["caption"] = str(result.get("caption") or "")
    return result


def normalize_document(step: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(step))
    result["fields"] = [normalize_field(field, index) for index, field in enumerate(result.get("fields") or [])]
    result["form_schema_version"] = FORM_SCHEMA_VERSION
    return result


def required_field_names(fields: Sequence[Mapping[str, Any]], explicit: Sequence[str]) -> list[str]:
    inferred = [
        str(field["name"]) for field in fields
        if field.get("required") and field.get("field_type") not in CONTENT_FIELD_TYPES | {"multiupload"}
    ]
    return list(dict.fromkeys([*explicit, *inferred]))


def prepare_create(values: Mapping[str, Any], survey_id: str, now_iso: str) -> StepConfigurationChange:
    result = dict(values)
    fields = [normalize_field(field, index) for index, field in enumerate(result.get("fields") or [])]
    result.update({
        "survey_id": survey_id,
        "fields": fields,
        "form_schema_version": FORM_SCHEMA_VERSION,
        "required_fields": required_field_names(fields, result.get("required_fields") or []),
        "is_active": True,
        "is_deleted": False,
        "current_version": 1,
        "created_at": now_iso,
    })
    for key in (
        "filter_tag", "skip_label", "action_label", "pending_message", "complete_message",
        "email_subject_enter", "email_body_enter", "email_subject_edit", "email_body_edit",
        "email_subject_leave", "email_body_leave",
    ):
        result[key] = result.get(key) or ""
    for key in ("required_uploads", "field_mappings", "conditions"):
        result[key] = result.get(key) or []
    result["translations"] = result.get("translations") or {}
    return StepConfigurationChange(result)


def prepare_update(
    values: Mapping[str, Any], supplied_fields: frozenset[str],
) -> StepConfigurationChange:
    result = {key: value for key, value in values.items() if value is not None}
    if "fields" in result:
        fields = [normalize_field(field, index) for index, field in enumerate(result["fields"] or [])]
        result["fields"] = fields
        result["form_schema_version"] = FORM_SCHEMA_VERSION
        if "required_fields" in result:
            result["required_fields"] = required_field_names(fields, result.get("required_fields") or [])
    unset = ("partner_user_fee_cents",) if "partner_user_fee_cents" in supplied_fields and values.get("partner_user_fee_cents") is None else ()
    return StepConfigurationChange(result, unset)


def condition_leaves(condition: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    children = condition.get("all_of") or condition.get("any_of")
    if children is None:
        yield condition
        return
    for child in children:
        yield from condition_leaves(child)


def _option_name(option: Any) -> str:
    if not isinstance(option, dict):
        return str(option)
    if "value" in option:
        return str(option["value"])
    return str(option.get("label") or "")


def relation_issues(steps: Sequence[Mapping[str, Any]]) -> tuple[StepRelationIssue, ...]:
    issues: list[StepRelationIssue] = []
    by_order = {step.get("order"): step for step in steps}
    if len(by_order) != len(steps):
        issues.append(StepRelationIssue(0, "Survey", "Doppelte Step-Reihenfolge vorhanden"))
    for step in steps:
        order = float(step.get("order") or 0)
        title = str(step.get("title") or "")
        fields = {field.get("name"): field for field in step.get("fields") or []}
        for required in step.get("required_fields") or []:
            if required not in fields:
                issues.append(StepRelationIssue(order, title, f"Requirement verweist auf unbekanntes Feld {required!r}"))
        options = {
            _option_name(option)
            for field in fields.values() if field.get("field_type") == "multiupload"
            for option in field.get("options") or []
        }
        for required in step.get("required_uploads") or []:
            if required not in options:
                issues.append(StepRelationIssue(order, title, f"Upload-Requirement {required!r} ist keine Dokumentoption"))
        for root in step.get("conditions") or []:
            for condition in condition_leaves(root):
                source = by_order.get(condition.get("source_step_order"))
                if source is None:
                    issues.append(StepRelationIssue(order, title, f"Condition verweist auf fehlenden Source-Step #{condition.get('source_step_order')}"))
                else:
                    field = condition.get("field")
                    source_fields = {item.get("name") for item in source.get("fields") or []} | SYSTEM_FIELDS
                    if field and field not in source_fields:
                        issues.append(StepRelationIssue(order, title, f"Condition verweist auf unbekanntes Feld {field!r} in Step #{source.get('order')}"))
                    target = condition.get("target_step_order")
                    if condition.get("action") == "redirect" and target not in by_order:
                        issues.append(StepRelationIssue(order, title, f"Redirect-Ziel #{target} fehlt"))
        for mapping in step.get("field_mappings") or []:
            source = by_order.get(mapping.get("source_step_order"))
            if source is None or mapping.get("source_field") not in {field.get("name") for field in source.get("fields") or []}:
                issues.append(StepRelationIssue(order, title, "Field-Mapping hat keine plausible Quelle"))
            if mapping.get("target_field") not in fields:
                issues.append(StepRelationIssue(order, title, "Field-Mapping hat kein plausibles Zielfeld"))
    return tuple(issues)
