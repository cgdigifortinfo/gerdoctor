"""Pure event configuration, dispatch and serialization rules."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from slices.event_system.models import EventOutcome, HandlerDecision

SUPPORTED_HANDLER_TYPES = frozenset({"email", "notification"})
SUPPORTED_CHANNELS = frozenset({"browser", "app"})


class EventRuleError(ValueError): pass
class UnsupportedHandlerType(EventRuleError): pass


def serialize_event(document: Mapping[str, Any] | None) -> dict[str, Any]:
    if not document:
        return {}
    result = {key: value for key, value in document.items() if key != "_id"}
    result["id"] = str(document.get("_id"))
    return result


def normalize_handler(handler: Mapping[str, Any], index: int) -> dict[str, Any]:
    raw_type = handler.get("type")
    if raw_type not in SUPPORTED_HANDLER_TYPES:
        raise UnsupportedHandlerType
    handler_type = str(raw_type)
    result: dict[str, Any] = {
        "id": handler.get("id") or f"handler-{index + 1}", "type": handler_type,
        "label": handler.get("label") or ("E-Mail senden" if handler_type == "email" else "Browser/App Notification"),
        "enabled": handler.get("enabled", True), "recipient": handler.get("recipient") or "user",
        "template_key": handler.get("template_key") or "",
    }
    if handler_type == "notification":
        result["channels"] = [item for item in (handler.get("channels") or []) if item in SUPPORTED_CHANNELS]
        result["provider"] = handler.get("provider") or "unconfigured"
    return result


def email_decision(payload: Mapping[str, Any], handler: Mapping[str, Any]) -> HandlerDecision:
    if handler.get("recipient") != "user":
        return HandlerDecision("skipped", "unsupported recipient")
    recipient = str(payload.get("user_email") or "")
    if not recipient:
        return HandlerDecision("skipped", "missing user_email")
    if payload.get("user_email_notifications_enabled") is False:
        return HandlerDecision("skipped", "user opt-out", recipient=recipient)
    template_key = str(handler.get("template_key") or "")
    if not template_key:
        return HandlerDecision("skipped", "missing template_key", recipient=recipient)
    return HandlerDecision("dispatch", recipient=recipient, template_key=template_key)


def notification_decision(payload: Mapping[str, Any], handler: Mapping[str, Any]) -> HandlerDecision:
    if handler.get("recipient") != "user":
        return HandlerDecision("skipped", "unsupported recipient")
    user_id = str(payload.get("user_id") or "")
    if not user_id:
        return HandlerDecision("skipped", "missing user_id")
    template_key = str(handler.get("template_key") or "")
    if not template_key:
        return HandlerDecision("skipped", "missing template_key")
    channels = tuple(item for item in (handler.get("channels") or ("browser", "app")) if item in SUPPORTED_CHANNELS)
    if not channels:
        return HandlerDecision("skipped", "no channels enabled", template_key=template_key)
    return HandlerDecision("dispatch", template_key=template_key, user_id=user_id,
                           channels=channels, provider=str(handler.get("provider") or "unconfigured"))


def skipped_result(decision: HandlerDecision) -> dict[str, Any]:
    result: dict[str, Any] = {"status": decision.status, "reason": decision.reason}
    if decision.recipient:
        result["recipient"] = decision.recipient
    if decision.template_key:
        result["template_key"] = decision.template_key
    return result


def event_outcome(results: Sequence[Mapping[str, Any]]) -> EventOutcome:
    failed = any(result.get("status") == "failed" for result in results)
    return EventOutcome("failed" if failed else "processed",
                        "One or more handlers failed" if failed else "",
                        tuple(dict(result) for result in results))


def pending_event(event_id: str, event_type: str, payload: Mapping[str, Any],
                  actor: Mapping[str, Any], timestamp: str) -> dict[str, Any]:
    return {"event_id": event_id, "event_type": event_type, "status": "pending",
            "payload": dict(payload), "actor": dict(actor), "handler_results": [],
            "created_at": timestamp, "processed_at": None, "attempts": 1, "error": ""}


def notification_outbox(event: Mapping[str, Any], handler: Mapping[str, Any],
                        decision: HandlerDecision, title: str, body: str,
                        timestamp: str) -> dict[str, Any]:
    handler_id = str(handler.get("id") or "notification")
    outbox_id = f"{event['event_id']}:{handler_id}"
    return {"outbox_id": outbox_id, "event_id": event["event_id"], "event_type": event["event_type"],
            "handler_id": handler.get("id"), "user_id": decision.user_id,
            "channels": list(decision.channels), "provider": decision.provider,
            "title": title, "body": body, "status": "pending_provider",
            "payload": dict(event.get("payload") or {}), "created_at": timestamp}
