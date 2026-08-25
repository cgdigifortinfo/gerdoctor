from __future__ import annotations

import pytest

from slices.event_system.domain import (
    UnsupportedHandlerType, email_decision, event_outcome, normalize_handler,
    notification_decision, notification_outbox, pending_event, serialize_event,
    skipped_result,
)
from slices.event_system.models import EventPage, HandlerDecision


def test_event_serialization_handles_missing_and_mongo_identifier():
    assert serialize_event(None) == {}
    assert serialize_event({"_id": 42, "event_type": "x"}) == {"id": "42", "event_type": "x"}
    assert EventPage(({"id": "1"},), 1).to_document() == {"events": [{"id": "1"}], "total": 1}


def test_handler_normalization_defaults_and_notification_specific_fields():
    email = normalize_handler({"type": "email"}, 1)
    assert email == {"id": "handler-2", "type": "email", "label": "E-Mail senden", "enabled": True,
                     "recipient": "user", "template_key": ""}
    notification = normalize_handler({"id": "n", "type": "notification", "label": "L", "enabled": False,
                                      "recipient": "admin", "template_key": "t",
                                      "channels": ["browser", "invalid", "app"], "provider": "push"}, 0)
    assert notification == {"id": "n", "type": "notification", "label": "L", "enabled": False,
                            "recipient": "admin", "template_key": "t",
                            "channels": ["browser", "app"], "provider": "push"}
    notification_defaults = normalize_handler({"type": "notification"}, 0)
    assert notification_defaults["label"] == "Browser/App Notification"
    assert notification_defaults["provider"] == "unconfigured"
    with pytest.raises(UnsupportedHandlerType): normalize_handler({"type": "webhook"}, 0)
    with pytest.raises(UnsupportedHandlerType): normalize_handler({}, 0)


@pytest.mark.parametrize("payload,handler,expected", [
    ({"user_email": "a@b.de"}, {"recipient": "admin"}, HandlerDecision("skipped", "unsupported recipient")),
    ({}, {"recipient": "user"}, HandlerDecision("skipped", "missing user_email")),
    ({"user_email": "a@b.de", "user_email_notifications_enabled": False}, {"recipient": "user"},
     HandlerDecision("skipped", "user opt-out", recipient="a@b.de")),
    ({"user_email": "a@b.de"}, {"recipient": "user"},
     HandlerDecision("skipped", "missing template_key", recipient="a@b.de")),
    ({"user_email": "a@b.de"}, {"recipient": "user", "template_key": "t"},
     HandlerDecision("dispatch", recipient="a@b.de", template_key="t")),
])
def test_email_dispatch_decisions(payload, handler, expected):
    assert email_decision(payload, handler) == expected


@pytest.mark.parametrize("payload,handler,expected", [
    ({"user_id": "u"}, {"recipient": "admin"}, HandlerDecision("skipped", "unsupported recipient")),
    ({}, {"recipient": "user"}, HandlerDecision("skipped", "missing user_id")),
    ({"user_id": "u"}, {"recipient": "user"}, HandlerDecision("skipped", "missing template_key")),
    ({"user_id": "u"}, {"recipient": "user", "template_key": "t", "channels": ["invalid"]},
     HandlerDecision("skipped", "no channels enabled", template_key="t")),
    ({"user_id": "u"}, {"recipient": "user", "template_key": "t"},
     HandlerDecision("dispatch", template_key="t", user_id="u", channels=("browser", "app"))),
    ({"user_id": "u"}, {"recipient": "user", "template_key": "t", "channels": ["app"], "provider": "push"},
     HandlerDecision("dispatch", template_key="t", user_id="u", channels=("app",), provider="push")),
])
def test_notification_dispatch_decisions(payload, handler, expected):
    assert notification_decision(payload, handler) == expected


def test_skipped_result_only_includes_available_context():
    assert skipped_result(HandlerDecision("skipped", "reason")) == {"status": "skipped", "reason": "reason"}
    assert skipped_result(HandlerDecision("skipped", "reason", "a@b.de", "tpl")) == {
        "status": "skipped", "reason": "reason", "recipient": "a@b.de", "template_key": "tpl",
    }


def test_event_outcome_pending_event_and_outbox_documents_are_stable():
    success = event_outcome(({"status": "queued"},))
    assert (success.status, success.error) == ("processed", "")
    failure = event_outcome(({"status": "failed"}, {"status": "queued"}))
    assert (failure.status, failure.error) == ("failed", "One or more handlers failed")
    assert pending_event("e", "type", {"x": 1}, {"id": "a"}, "now") == {
        "event_id": "e", "event_type": "type", "status": "pending", "payload": {"x": 1},
        "actor": {"id": "a"}, "handler_results": [], "created_at": "now", "processed_at": None,
        "attempts": 1, "error": "",
    }
    event = {"event_id": "e", "event_type": "type", "payload": {"x": 1}}
    handler = {"id": "h"}
    decision = HandlerDecision("dispatch", template_key="t", user_id="u", channels=("app",), provider="push")
    outbox = notification_outbox(event, handler, decision, "Title", "Body", "now")
    assert outbox == {
        "outbox_id": "e:h", "event_id": "e", "event_type": "type", "handler_id": "h",
        "user_id": "u", "channels": ["app"], "provider": "push", "title": "Title",
        "body": "Body", "status": "pending_provider", "payload": {"x": 1}, "created_at": "now",
    }
    assert notification_outbox(event, {}, decision, "T", "B", "now")["outbox_id"] == "e:notification"
