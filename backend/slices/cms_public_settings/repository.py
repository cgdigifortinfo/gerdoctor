"""MongoDB adapter for CMS content and global site settings."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast


class MongoCmsPublicSettingsRepository:
    def __init__(self, database: Any) -> None:
        self._db = database

    async def cms_sections(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], await self._db.cms_content.find({}, {"_id": 0}).to_list(100))

    async def cms_section(self, section: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, await self._db.cms_content.find_one({"section": section}, {"_id": 0}))

    async def save_cms_section(self, section: str, fields: Mapping[str, Any]) -> None:
        await self._db.cms_content.update_one({"section": section}, {"$set": dict(fields)}, upsert=True)

    async def settings(self) -> dict[str, Any]:
        value = await self._db.site_settings.find_one({"_key": "global"}, {"_id": 0, "_key": 0})
        return cast(dict[str, Any], value or {})

    async def update_settings(self, fields: Mapping[str, Any]) -> None:
        await self._db.site_settings.update_one({"_key": "global"}, {"$set": dict(fields)}, upsert=True)

    async def insert_settings(self, fields: Mapping[str, Any]) -> None:
        await self._db.site_settings.insert_one({"_key": "global", **dict(fields)})
