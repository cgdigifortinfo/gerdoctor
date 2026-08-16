"""Persistent domain-event dispatcher with configurable handlers.

Events are written before they are handled. This keeps business actions and
notifications decoupled and gives admins a durable history that can be retried.
The first handler type is email; additional handler types can be registered in
``HANDLER_DISPATCHERS`` without changing the business endpoints.
"""
import logging
import uuid
from datetime import datetime, timezone

from database import db
from helpers import render_notification, send_rendered_email


logger = logging.getLogger("server")


DEFAULT_EVENT_CONFIGS = {
    "partner.step.completed": {
        "label": "Partner schließt Step ab",
        "description": "Wird ausgelöst, wenn ein Partner einen verwalteten Step für einen User abschließt.",
        "enabled": True,
        "handlers": [
            {
                "id": "notify-user-email",
                "type": "email",
                "label": "User per E-Mail informieren",
                "enabled": True,
                "recipient": "user",
                "template_key": "user_milestone_completed",
            },
            {
                "id": "notify-user-browser-app",
                "type": "notification",
                "label": "Browser/App Notification",
                "enabled": False,
                "recipient": "user",
                "template_key": "user_milestone_completed",
                "channels": ["browser", "app"],
                "provider": "unconfigured",
            },
        ],
    },
    "partner.step.rejected": {
        "label": "Partner lehnt Step ab",
        "description": "Setzt den User einen sichtbaren Schritt zurück und informiert ihn über den Grund.",
        "enabled": True,
        "handlers": [
            {
                "id": "notify-user-email",
                "type": "email",
                "label": "User per E-Mail informieren",
                "enabled": True,
                "recipient": "user",
                "template_key": "user_partner_step_rejected",
            },
            {
                "id": "notify-user-browser-app",
                "type": "notification",
                "label": "Browser/App Notification",
                "enabled": False,
                "recipient": "user",
                "template_key": "user_partner_step_rejected",
                "channels": ["browser", "app"],
                "provider": "unconfigured",
            },
        ],
    },
    "partner.document.uploaded": {
        "label": "Partner lädt Dokument hoch",
        "description": "Protokolliert Nachweise, die ein Partner im User-Step hinterlegt.",
        "enabled": True,
        "handlers": [],
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def ensure_event_configs() -> None:
    """Seed known event types without overwriting admin configuration."""
    now = _now()
    for event_type, defaults in DEFAULT_EVENT_CONFIGS.items():
        existing = await db.event_configs.find_one({"event_type": event_type})
        if not existing:
            await db.event_configs.insert_one({
                "event_type": event_type,
                **defaults,
                "created_at": now,
                "updated_at": now,
            })
            continue
        existing_ids = {handler.get("id") for handler in (existing.get("handlers") or [])}
        missing_handlers = [
            handler for handler in (defaults.get("handlers") or [])
            if handler.get("id") not in existing_ids
        ]
        if missing_handlers:
            await db.event_configs.update_one(
                {"event_type": event_type},
                {"$push": {"handlers": {"$each": missing_handlers}}, "$set": {"updated_at": now}},
            )


def serialize_event_document(document: dict | None) -> dict:
    if not document:
        return {}
    result = {key: value for key, value in document.items() if key != "_id"}
    result["id"] = str(document.get("_id"))
    return result


async def _handle_email(event: dict, handler: dict) -> dict:
    payload = event.get("payload") or {}
    if handler.get("recipient") != "user":
        return {"status": "skipped", "reason": "unsupported recipient"}
    recipient = payload.get("user_email")
    if not recipient:
        return {"status": "skipped", "reason": "missing user_email"}
    if payload.get("user_email_notifications_enabled") is False:
        return {"status": "skipped", "reason": "user opt-out", "recipient": recipient}
    template_key = handler.get("template_key")
    if not template_key:
        return {"status": "skipped", "reason": "missing template_key", "recipient": recipient}
    result = await send_rendered_email(recipient, template_key, payload)
    return {**result, "recipient": recipient, "template_key": template_key}


async def _handle_notification(event: dict, handler: dict) -> dict:
    """Render a provider-neutral Browser/App notification into the outbox."""
    payload = event.get("payload") or {}
    if handler.get("recipient") != "user":
        return {"status": "skipped", "reason": "unsupported recipient"}
    user_id = payload.get("user_id")
    if not user_id:
        return {"status": "skipped", "reason": "missing user_id"}
    template_key = handler.get("template_key")
    if not template_key:
        return {"status": "skipped", "reason": "missing template_key"}
    rendered = await render_notification(template_key, payload)
    if not rendered or not (rendered.get("title") or rendered.get("body")):
        return {"status": "skipped", "reason": "notification content missing", "template_key": template_key}
    channels = [channel for channel in (handler.get("channels") or ["browser", "app"]) if channel in ("browser", "app")]
    if not channels:
        return {"status": "skipped", "reason": "no channels enabled", "template_key": template_key}
    outbox_id = f"{event['event_id']}:{handler.get('id', 'notification')}"
    await db.notification_outbox.update_one(
        {"outbox_id": outbox_id},
        {"$setOnInsert": {
            "outbox_id": outbox_id,
            "event_id": event["event_id"],
            "event_type": event["event_type"],
            "handler_id": handler.get("id"),
            "user_id": user_id,
            "channels": channels,
            "provider": handler.get("provider") or "unconfigured",
            "title": rendered["title"],
            "body": rendered["body"],
            "status": "pending_provider",
            "payload": payload,
            "created_at": _now(),
        }},
        upsert=True,
    )
    return {
        "status": "queued",
        "outbox_id": outbox_id,
        "template_key": template_key,
        "channels": channels,
        "provider": handler.get("provider") or "unconfigured",
    }


HANDLER_DISPATCHERS = {
    "email": _handle_email,
    "notification": _handle_notification,
}


async def process_domain_event(event_id: str) -> dict:
    event = await db.domain_events.find_one({"event_id": event_id})
    if not event:
        raise ValueError("Event not found")
    config = await db.event_configs.find_one({"event_type": event["event_type"]})
    if not config or config.get("enabled") is False:
        await db.domain_events.update_one(
            {"event_id": event_id},
            {"$set": {"status": "skipped", "processed_at": _now(), "handler_results": [], "error": "Event disabled"}},
        )
        return serialize_event_document(await db.domain_events.find_one({"event_id": event_id}))

    results = []
    failed = False
    for handler in config.get("handlers") or []:
        if handler.get("enabled") is False:
            results.append({"handler_id": handler.get("id"), "type": handler.get("type"), "status": "disabled"})
            continue
        dispatcher = HANDLER_DISPATCHERS.get(handler.get("type"))
        if not dispatcher:
            results.append({"handler_id": handler.get("id"), "type": handler.get("type"), "status": "failed", "error": "Unknown handler type"})
            failed = True
            continue
        try:
            result = await dispatcher(event, handler)
            results.append({"handler_id": handler.get("id"), "type": handler.get("type"), **result})
            if result.get("status") == "failed":
                failed = True
        except Exception as exc:
            logger.exception("Domain event handler failed for %s", event_id)
            results.append({"handler_id": handler.get("id"), "type": handler.get("type"), "status": "failed", "error": str(exc)})
            failed = True

    await db.domain_events.update_one(
        {"event_id": event_id},
        {"$set": {
            "status": "failed" if failed else "processed",
            "processed_at": _now(),
            "handler_results": results,
            "error": "One or more handlers failed" if failed else "",
        }},
    )
    return serialize_event_document(await db.domain_events.find_one({"event_id": event_id}))


async def emit_domain_event(event_type: str, payload: dict, actor: dict | None = None) -> dict:
    """Persist and synchronously dispatch a domain event.

    Persisting first means the event remains visible/retryable even when a
    notification provider fails. The dispatcher can later be moved to a queue
    worker without changing emitters or the stored schema.
    """
    await ensure_event_configs()
    event_id = str(uuid.uuid4())
    now = _now()
    await db.domain_events.insert_one({
        "event_id": event_id,
        "event_type": event_type,
        "status": "pending",
        "payload": payload or {},
        "actor": actor or {},
        "handler_results": [],
        "created_at": now,
        "processed_at": None,
        "attempts": 1,
        "error": "",
    })
    return await process_domain_event(event_id)


async def retry_domain_event(event_id: str) -> dict:
    result = await db.domain_events.update_one(
        {"event_id": event_id},
        {"$set": {"status": "pending", "error": ""}, "$inc": {"attempts": 1}},
    )
    if result.matched_count == 0:
        raise ValueError("Event not found")
    return await process_domain_event(event_id)
