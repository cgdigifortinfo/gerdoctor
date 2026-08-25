"""MongoDB audit-trail adapter."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from slices.audit_trail.models import AuditEntry, AuditPage


class MongoAuditTrailRepository:
    def __init__(self, database: Any) -> None: self._db = database

    async def append(self, entry: AuditEntry) -> None:
        await self._db.audit_logs.insert_one(entry.to_document())

    async def page(self, query: Mapping[str, Any], limit: int, skip: int) -> AuditPage:
        mongo_query = dict(query)
        total = int(await self._db.audit_logs.count_documents(mongo_query))
        cursor = self._db.audit_logs.find(mongo_query, {"_id": 0}).sort("timestamp", -1).skip(skip)
        logs = await (cursor.limit(limit).to_list(limit) if limit > 0 else cursor.to_list(total))
        actions = await self._db.audit_logs.distinct("action")
        return AuditPage(tuple(cast(list[dict[str, Any]], logs)), total,
                         tuple(str(action) for action in actions))

    async def ensure_indexes(self) -> None:
        await self._db.audit_logs.create_index([("timestamp", -1)])
