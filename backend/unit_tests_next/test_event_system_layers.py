from __future__ import annotations

import asyncio

import pytest

from slices.email_notifications.models import DeliveryResult, RenderedNotification
from slices.email_notifications.service import TemplateNotFound
from slices.event_system.adapters import MessageEventNotifier
from slices.event_system.models import EventOutcome, EventPage
from slices.event_system.repository import MongoEventRepository
from slices.event_system.service import EventConfigNotFound, EventNotFound, EventSystemService
from slices.event_system.web import event_system_http_error


def run(coroutine): return asyncio.run(coroutine)


class Repository:
    def __init__(self):
        self.event_rows = {}
        self.config_rows = {}
        self.outbox = []
        self.finished = None
        self.ensured = None
        self.retry_matches = True
        self.updated = None
    async def ensure_configs(self, defaults, timestamp): self.ensured = (defaults, timestamp)
    async def event(self, event_id): return self.event_rows.get(event_id)
    async def config(self, event_type): return self.config_rows.get(event_type)
    async def insert_event(self, event): self.event_rows[event["event_id"]] = dict(event)
    async def finish_event(self, event_id, outcome, timestamp):
        self.finished = (event_id, outcome, timestamp)
        self.event_rows[event_id].update(status=outcome.status, handler_results=list(outcome.handler_results),
                                         error=outcome.error, processed_at=timestamp)
    async def skip_event(self, event_id, timestamp):
        self.event_rows[event_id].update(status="skipped", error="Event disabled", processed_at=timestamp)
    async def prepare_retry(self, event_id): return self.retry_matches
    async def enqueue_notification(self, document): self.outbox.append(dict(document))
    async def configs(self): return list(self.config_rows.values())
    async def update_config(self, event_type, fields):
        self.updated = (event_type, dict(fields))
        if event_type not in self.config_rows: return None
        self.config_rows[event_type].update(fields)
        return self.config_rows[event_type]
    async def events(self, query, limit, skip): return EventPage(({"query": dict(query)},), 1)


class Notifier:
    def __init__(self):
        self.delivery = DeliveryResult("success")
        self.rendered = RenderedNotification("Title", "Body")
        self.raise_email = None
    async def email(self, recipient, template_key, variables):
        if self.raise_email: raise self.raise_email
        return self.delivery
    async def notification(self, template_key, variables): return self.rendered


def service(repository=None, notifier=None):
    return EventSystemService(repository or Repository(), notifier or Notifier(), lambda: "now", lambda: "event-id")


def test_service_ensures_lists_updates_and_pages_configs():
    repository = Repository()
    repository.config_rows["type"] = {"event_type": "type", "enabled": True}
    subject = service(repository)
    run(subject.ensure_configs())
    assert repository.ensured[1] == "now"
    assert run(subject.configs()) == [{"event_type": "type", "enabled": True}]
    updated = run(subject.update_config("type", {"handlers": [{"type": "email"}]}))
    assert updated["handlers"][0]["id"] == "handler-1"
    assert repository.updated[1]["updated_at"] == "now"
    page = run(subject.events("type", "failed", 10, 2))
    assert page.events[0]["query"] == {"event_type": "type", "status": "failed"}
    assert run(subject.events("", "", 0, 0)).events[0]["query"] == {}
    with pytest.raises(EventConfigNotFound): run(subject.update_config("missing", {}))
    repository.config_rows["race"] = {"event_type": "race"}
    async def vanished(event_type, fields): return None
    repository.update_config = vanished
    with pytest.raises(EventConfigNotFound): run(subject.update_config("race", {}))


def test_process_missing_disabled_and_empty_handler_event_paths():
    repository = Repository(); subject = service(repository)
    with pytest.raises(EventNotFound): run(subject.process("missing"))
    repository.event_rows["e"] = {"_id": 1, "event_id": "e", "event_type": "type"}
    assert run(subject.process("e"))["status"] == "skipped"
    repository.config_rows["type"] = {"enabled": True, "handlers": []}
    assert run(subject.process("e"))["status"] == "processed"


def test_process_dispatches_disabled_unknown_email_and_notification_handlers():
    repository, notifier = Repository(), Notifier()
    repository.event_rows["e"] = {"_id": 1, "event_id": "e", "event_type": "type",
                                  "payload": {"user_email": "a@b.de", "user_id": "u"}}
    repository.config_rows["type"] = {"enabled": True, "handlers": [
        {"id": "off", "type": "email", "enabled": False},
        {"id": "unknown", "type": "webhook"},
        {"id": "mail", "type": "email", "recipient": "user", "template_key": "tpl"},
        {"id": "notice", "type": "notification", "recipient": "user", "template_key": "tpl"},
    ]}
    result = run(service(repository, notifier).process("e"))
    assert result["status"] == "failed"
    statuses = [item["status"] for item in result["handler_results"]]
    assert statuses == ["disabled", "failed", "success", "queued"]
    assert repository.outbox[0]["outbox_id"] == "e:notice"


def test_process_handles_preflight_empty_notification_and_dispatch_exception():
    repository, notifier = Repository(), Notifier()
    repository.event_rows["e"] = {"_id": 1, "event_id": "e", "event_type": "type", "payload": {}}
    repository.config_rows["type"] = {"enabled": True, "handlers": [
        {"id": "mail", "type": "email", "recipient": "user", "template_key": "tpl"},
        {"id": "notice", "type": "notification", "recipient": "user", "template_key": "tpl"},
    ]}
    result = run(service(repository, notifier).process("e"))
    assert [item["reason"] for item in result["handler_results"]] == ["missing user_email", "missing user_id"]
    repository.event_rows["e"]["payload"] = {"user_email": "a@b.de", "user_id": "u"}
    notifier.rendered = None
    notifier.raise_email = RuntimeError("delivery failed")
    result = run(service(repository, notifier).process("e"))
    assert result["status"] == "failed"
    assert result["handler_results"][0]["error"] == "delivery failed"
    assert result["handler_results"][1]["reason"] == "notification content missing"
    notifier.raise_email = None
    notifier.rendered = RenderedNotification("", "")
    assert run(service(repository, notifier).process("e"))["handler_results"][1]["reason"] == "notification content missing"


def test_emit_and_retry_persist_before_processing_and_reject_unknown_retry():
    repository = Repository()
    repository.config_rows["type"] = {"enabled": True, "handlers": []}
    subject = service(repository)
    emitted = run(subject.emit("type", {"x": 1}, None))
    assert emitted["event_id"] == "event-id" and emitted["actor"] == {}
    assert run(subject.retry("event-id"))["status"] == "processed"
    repository.retry_matches = False
    with pytest.raises(EventNotFound): run(subject.retry("missing"))


class Messages:
    async def send_rendered(self, recipient, template_key, variables): return DeliveryResult("success")
    async def notification(self, template_key, variables):
        if template_key == "missing": raise TemplateNotFound
        return RenderedNotification("T", "B")


def test_message_adapter_maps_email_notification_and_missing_template():
    adapter = MessageEventNotifier(Messages())
    assert run(adapter.email("a@b.de", "t", {})).status == "success"
    assert run(adapter.notification("t", {})) == RenderedNotification("T", "B")
    assert run(adapter.notification("missing", {})) is None


def test_web_error_mapping_is_specific_and_has_safe_fallback():
    assert event_system_http_error(EventNotFound()).detail == "Event not found"
    assert event_system_http_error(EventConfigNotFound()).detail == "Event type not found"
    from slices.event_system.domain import UnsupportedHandlerType
    assert event_system_http_error(UnsupportedHandlerType()).status_code == 422
    assert event_system_http_error(ValueError()).status_code == 400


class Result:
    def __init__(self, matched_count=1): self.matched_count = matched_count


class Cursor:
    def __init__(self, rows): self.rows = rows; self.limit_value = None
    def sort(self, *args): return self
    def skip(self, value): self.rows = self.rows[value:]; return self
    def limit(self, value): self.limit_value = value; return self
    async def to_list(self, value): return self.rows[:value]


class Collection:
    def __init__(self, rows=()): self.rows = [dict(row) for row in rows]; self.inserts = []; self.updates = []
    async def find_one(self, query, *args):
        return next((row for row in self.rows if all(row.get(k) == v for k, v in query.items())), None)
    async def insert_one(self, document): self.inserts.append(dict(document)); self.rows.append(dict(document))
    async def update_one(self, query, update, upsert=False):
        self.updates.append((query, update, upsert))
        return Result(0 if query.get("event_id") == "missing" else 1)
    def find(self, *args): return Cursor(list(self.rows))
    async def count_documents(self, query): return len(self.rows)


class Database:
    def __init__(self):
        self.event_configs = Collection()
        self.domain_events = Collection(({"_id": 1, "event_id": "e", "event_type": "type"},))
        self.notification_outbox = Collection()


def test_mongo_repository_covers_config_event_outbox_retry_and_page_operations():
    database = Database(); repository = MongoEventRepository(database)
    defaults = {
        "new": {"handlers": []},
        "existing": {"handlers": [{"id": "new-handler"}]},
        "complete": {"handlers": [{"id": "present"}]},
    }
    database.event_configs.rows.extend([
        {"event_type": "existing", "handlers": []},
        {"event_type": "complete", "handlers": [{"id": "present"}]},
    ])
    run(repository.ensure_configs(defaults, "now"))
    assert database.event_configs.inserts[0]["event_type"] == "new"
    assert database.event_configs.updates[0][1]["$push"]["handlers"]["$each"][0]["id"] == "new-handler"
    assert run(repository.event("e"))["event_type"] == "type"
    assert run(repository.config("existing"))["event_type"] == "existing"
    run(repository.insert_event({"event_id": "second", "event_type": "type"}))
    outcome = EventOutcome("processed", "", ({"status": "success"},))
    run(repository.finish_event("e", outcome, "now"))
    run(repository.skip_event("e", "later"))
    assert run(repository.prepare_retry("e")) is True
    assert run(repository.prepare_retry("missing")) is False
    run(repository.enqueue_notification({"outbox_id": "o"}))
    assert database.notification_outbox.updates[0][2] is True
    assert len(run(repository.configs())) == 3
    assert run(repository.update_config("existing", {"enabled": False}))["event_type"] == "existing"
    assert len(run(repository.events({}, 1, 0)).events) == 1
    assert len(run(repository.events({}, 0, 1)).events) == 1
