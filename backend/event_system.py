"""Compatibility facade for the extracted persistent event-system slice."""
from __future__ import annotations

from typing import Any

from database import db
from helpers import email_notifications_service
from infrastructure.clock import system_utc_clock
from infrastructure.identifiers import uuid4_generator
from slices.event_system.adapters import MessageEventNotifier
from slices.event_system.defaults import DEFAULT_EVENT_CONFIGS
from slices.event_system.domain import serialize_event as serialize_event_document
from slices.event_system.repository import MongoEventRepository
from slices.event_system.service import EventNotFound, EventSystemService

event_system_service = EventSystemService(
    MongoEventRepository(db), MessageEventNotifier(email_notifications_service),
    system_utc_clock.now_iso, uuid4_generator.new,
)


async def ensure_event_configs() -> None:
    await event_system_service.ensure_configs()


async def process_domain_event(event_id: str) -> dict[str, Any]:
    try:
        return await event_system_service.process(event_id)
    except EventNotFound as error:
        raise ValueError("Event not found") from error


async def emit_domain_event(event_type: str, payload: dict[str, Any],
                            actor: dict[str, Any] | None = None) -> dict[str, Any]:
    return await event_system_service.emit(event_type, payload, actor)


async def retry_domain_event(event_id: str) -> dict[str, Any]:
    try:
        return await event_system_service.retry(event_id)
    except EventNotFound as error:
        raise ValueError("Event not found") from error
