"""Application services for editable CMS content and exposed settings."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from slices.cms_public_settings.domain import (
    admin_settings, cms_seed_update, cms_update_fields, editable_settings,
    normalize_cms_payload, public_settings,
)
from slices.cms_public_settings.ports import CmsPublicSettingsRepository


class CmsPublicSettingsService:
    def __init__(self, repository: CmsPublicSettingsRepository, now: Callable[[], str],
                 secret_fields: frozenset[str]) -> None:
        self._repository, self._now, self._secret_fields = repository, now, secret_fields

    async def all_content(self) -> dict[str, dict[str, dict[str, Any]]]:
        rows = await self._repository.cms_sections()
        return {str(row["section"]): normalize_cms_payload(
            row.get("content"), row.get("translations")).response() for row in rows}

    async def content(self, section: str) -> dict[str, dict[str, Any]]:
        row = await self._repository.cms_section(section)
        return normalize_cms_payload(row.get("content"), row.get("translations")).response() if row else {
            "content": {}, "translations": {}}

    async def update_content(self, section: str, content: object, translations: object,
                             include_translations: bool) -> None:
        await self._repository.save_cms_section(section, cms_update_fields(
            section, content, translations, include_translations, self._now()))

    async def admin_settings(self, stripe_status: Mapping[str, Any]) -> dict[str, Any]:
        result = admin_settings(await self._repository.settings(), self._secret_fields)
        result["stripe"] = dict(stripe_status)
        return result

    async def update_settings(self, values: Mapping[str, Any]) -> list[str]:
        fields = editable_settings(values)
        if fields:
            await self._repository.update_settings(fields)
        return list(fields)

    async def public_settings(self, stripe_status: Mapping[str, Any]) -> dict[str, Any]:
        hidden = self._secret_fields | {"stripe_test_publishable_key", "stripe_live_publishable_key"}
        result = public_settings(await self._repository.settings(), hidden)
        result["stripe"] = dict(stripe_status)
        return result

    async def seed(self, defaults: Mapping[str, Mapping[str, Any]],
                   english_defaults: Mapping[str, Mapping[str, Any]],
                   default_settings: Mapping[str, Any]) -> None:
        for section, values in defaults.items():
            existing = await self._repository.cms_section(section)
            if existing is None:
                fields: dict[str, Any] = {"section": section, "content": dict(values), "created_at": self._now()}
                if section in english_defaults:
                    fields["translations"] = {"en": dict(english_defaults[section])}
                await self._repository.save_cms_section(section, fields)
            else:
                update = cms_seed_update(existing, values, english_defaults.get(section))
                if update:
                    await self._repository.save_cms_section(section, update)
        if not await self._repository.settings():
            await self._repository.insert_settings({**default_settings, "created_at": self._now()})
