"""Application service for durable event dispatch and retries."""
from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

from slices.event_system.defaults import DEFAULT_EVENT_CONFIGS
from slices.event_system.domain import (
    email_decision, event_outcome, normalize_handler, notification_decision,
    notification_outbox, pending_event, serialize_event, skipped_result,
)
from slices.event_system.models import EventPage
from slices.event_system.ports import EventNotifier, EventRepository

logger = logging.getLogger("server")


class EventNotFound(LookupError): pass
class EventConfigNotFound(LookupError): pass


class EventSystemService:
    def __init__(self, repository: EventRepository, notifier: EventNotifier,
                 now: Callable[[], str], new_id: Callable[[], str]) -> None:
        self._repository, self._notifier = repository, notifier
        self._now, self._new_id = now, new_id

    async def ensure_configs(self) -> None:
        await self._repository.ensure_configs(DEFAULT_EVENT_CONFIGS, self._now())

    async def _email(self, event: Mapping[str, Any], handler: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(event.get("payload") or {})
        decision = email_decision(payload, handler)
        if decision.status != "dispatch": return skipped_result(decision)
        result = await self._notifier.email(decision.recipient, decision.template_key, payload)
        return {**result.to_document(), "recipient": decision.recipient, "template_key": decision.template_key}

    async def _notification(self, event: Mapping[str, Any], handler: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(event.get("payload") or {})
        decision = notification_decision(payload, handler)
        if decision.status != "dispatch": return skipped_result(decision)
        rendered = await self._notifier.notification(decision.template_key, payload)
        if rendered is None or not (rendered.title or rendered.body):
            return {"status": "skipped", "reason": "notification content missing",
                    "template_key": decision.template_key}
        document = notification_outbox(event, handler, decision, rendered.title, rendered.body, self._now())
        await self._repository.enqueue_notification(document)
        return {"status": "queued", "outbox_id": document["outbox_id"],
                "template_key": decision.template_key, "channels": list(decision.channels),
                "provider": decision.provider}

    async def process(self, event_id: str) -> dict[str, Any]:
        event = await self._repository.event(event_id)
        if event is None: raise EventNotFound(event_id)
        config = await self._repository.config(str(event["event_type"]))
        if not config or config.get("enabled") is False:
            await self._repository.skip_event(event_id, self._now())
            return serialize_event(await self._repository.event(event_id))
        results: list[dict[str, Any]] = []
        dispatchers = {"email": self._email, "notification": self._notification}
        for handler in config.get("handlers") or []:
            base = {"handler_id": handler.get("id"), "type": handler.get("type")}
            if handler.get("enabled") is False:
                results.append({**base, "status": "disabled"})
                continue
            dispatcher = dispatchers.get(handler.get("type"))
            if dispatcher is None:
                results.append({**base, "status": "failed", "error": "Unknown handler type"})
                continue
            try:
                results.append({**base, **await dispatcher(event, handler)})
            except Exception as error:
                logger.exception("Domain event handler failed for %s", event_id)
                results.append({**base, "status": "failed", "error": str(error)})
        await self._repository.finish_event(event_id, event_outcome(results), self._now())
        return serialize_event(await self._repository.event(event_id))

    async def emit(self, event_type: str, payload: Mapping[str, Any],
                   actor: Mapping[str, Any] | None = None) -> dict[str, Any]:
        await self.ensure_configs()
        event_id, timestamp = self._new_id(), self._now()
        await self._repository.insert_event(pending_event(event_id, event_type, payload, actor or {}, timestamp))
        return await self.process(event_id)

    async def retry(self, event_id: str) -> dict[str, Any]:
        if not await self._repository.prepare_retry(event_id): raise EventNotFound(event_id)
        return await self.process(event_id)

    async def configs(self) -> list[dict[str, Any]]:
        await self.ensure_configs()
        return await self._repository.configs()

    async def update_config(self, event_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        await self.ensure_configs()
        if await self._repository.config(event_type) is None: raise EventConfigNotFound(event_type)
        fields = dict(payload)
        if "handlers" in fields:
            fields["handlers"] = [normalize_handler(item, index) for index, item in enumerate(fields["handlers"])]
        fields["updated_at"] = self._now()
        updated = await self._repository.update_config(event_type, fields)
        if updated is None: raise EventConfigNotFound(event_type)
        return updated

    async def events(self, event_type: str, status: str, limit: int, skip: int) -> EventPage:
        query = {key: value for key, value in (("event_type", event_type), ("status", status)) if value}
        return await self._repository.events(query, limit, skip)
