"""MongoDB persistence for event configs, events and notification outbox."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from slices.event_system.domain import serialize_event
from slices.event_system.models import EventOutcome, EventPage


class MongoEventRepository:
    def __init__(self, database: Any) -> None: self._db = database

    async def ensure_configs(self, defaults: Mapping[str, Mapping[str, Any]], timestamp: str) -> None:
        for event_type, values in defaults.items():
            existing = await self._db.event_configs.find_one({"event_type": event_type})
            if not existing:
                await self._db.event_configs.insert_one({"event_type": event_type, **values,
                                                         "created_at": timestamp, "updated_at": timestamp})
                continue
            existing_ids = {item.get("id") for item in (existing.get("handlers") or [])}
            missing = [dict(item) for item in (values.get("handlers") or []) if item.get("id") not in existing_ids]
            if missing:
                await self._db.event_configs.update_one(
                    {"event_type": event_type},
                    {"$push": {"handlers": {"$each": missing}}, "$set": {"updated_at": timestamp}},
                )

    async def event(self, event_id: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, await self._db.domain_events.find_one({"event_id": event_id}))

    async def config(self, event_type: str) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, await self._db.event_configs.find_one({"event_type": event_type}))

    async def insert_event(self, event: Mapping[str, Any]) -> None:
        await self._db.domain_events.insert_one(dict(event))

    async def finish_event(self, event_id: str, outcome: EventOutcome, timestamp: str) -> None:
        await self._db.domain_events.update_one({"event_id": event_id}, {"$set": {
            "status": outcome.status, "processed_at": timestamp,
            "handler_results": list(outcome.handler_results), "error": outcome.error,
        }})

    async def skip_event(self, event_id: str, timestamp: str) -> None:
        await self._db.domain_events.update_one({"event_id": event_id}, {"$set": {
            "status": "skipped", "processed_at": timestamp, "handler_results": [], "error": "Event disabled",
        }})

    async def prepare_retry(self, event_id: str) -> bool:
        result = await self._db.domain_events.update_one(
            {"event_id": event_id}, {"$set": {"status": "pending", "error": ""}, "$inc": {"attempts": 1}},
        )
        return bool(result.matched_count)

    async def enqueue_notification(self, document: Mapping[str, Any]) -> None:
        await self._db.notification_outbox.update_one(
            {"outbox_id": document["outbox_id"]}, {"$setOnInsert": dict(document)}, upsert=True,
        )

    async def configs(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], await self._db.event_configs.find({}, {"_id": 0}).sort("event_type", 1).to_list(100))

    async def update_config(self, event_type: str, fields: Mapping[str, Any]) -> dict[str, Any] | None:
        await self._db.event_configs.update_one({"event_type": event_type}, {"$set": dict(fields)})
        return cast(dict[str, Any] | None, await self._db.event_configs.find_one({"event_type": event_type}, {"_id": 0}))

    async def events(self, query: Mapping[str, Any], limit: int, skip: int) -> EventPage:
        total = await self._db.domain_events.count_documents(dict(query))
        cursor = self._db.domain_events.find(dict(query)).sort("created_at", -1).skip(skip)
        documents = await (cursor.limit(limit).to_list(limit) if limit > 0 else cursor.to_list(total))
        return EventPage(tuple(serialize_event(item) for item in documents), total)
