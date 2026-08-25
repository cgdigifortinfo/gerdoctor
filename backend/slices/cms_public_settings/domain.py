"""Pure rules for CMS payloads and safely exposed settings."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from slices.cms_public_settings.models import CmsPayload

MASKED_VALUE = "••••••••"


def normalize_cms_payload(content: object, translations: object) -> CmsPayload:
    """Unwrap legacy response-shaped content without mutating its input."""
    normalized_content = dict(content) if isinstance(content, dict) else {}
    normalized_translations = dict(translations) if isinstance(translations, dict) else {}
    while isinstance(normalized_content.get("content"), dict):
        wrapper = normalized_content
        nested = dict(wrapper["content"])
        outer = {key: value for key, value in wrapper.items()
                 if key not in {"content", "translations", "section"}}
        normalized_content = {**nested, **outer}
        nested_translations = wrapper.get("translations")
        if isinstance(nested_translations, dict):
            normalized_translations = {**nested_translations, **normalized_translations}
    return CmsPayload(normalized_content, normalized_translations)


def cms_update_fields(section: str, content: object, translations: object,
                      include_translations: bool, timestamp: str) -> dict[str, Any]:
    payload = normalize_cms_payload(content, translations)
    fields: dict[str, Any] = {"section": section, "content": payload.content, "updated_at": timestamp}
    if include_translations:
        fields["translations"] = payload.translations
    return fields


def editable_settings(values: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None and value != MASKED_VALUE}


def admin_settings(values: Mapping[str, Any], secret_fields: Iterable[str]) -> dict[str, Any]:
    result = dict(values)
    for field in secret_fields:
        if result.get(field):
            result[field] = MASKED_VALUE
    return result


def public_settings(values: Mapping[str, Any], hidden_fields: Iterable[str]) -> dict[str, Any]:
    result = dict(values)
    for field in hidden_fields:
        result.pop(field, None)
    return result


def cms_seed_update(existing: Mapping[str, Any], defaults: Mapping[str, Any],
                    english_defaults: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = normalize_cms_payload(existing.get("content"), existing.get("translations"))
    update: dict[str, Any] = {}
    merged_content = {**payload.content, **{k: v for k, v in defaults.items() if k not in payload.content}}
    if merged_content != (existing.get("content") or {}):
        update["content"] = merged_content
    if english_defaults is not None:
        translations = payload.translations
        english_value = translations.get("en")
        english: dict[str, Any] = dict(english_value) if isinstance(english_value, dict) else {}
        merged_english = {**english, **{k: v for k, v in english_defaults.items() if k not in english}}
        merged_translations = {**translations, "en": merged_english}
        if merged_translations != (existing.get("translations") or {}):
            update["translations"] = merged_translations
    return update
