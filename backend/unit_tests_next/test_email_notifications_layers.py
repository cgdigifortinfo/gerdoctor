from __future__ import annotations

import smtplib
import asyncio
from unittest.mock import patch

import pytest

from infrastructure.smtp_email_gateway import SmtpEmailGateway
from slices.email_notifications.defaults import default_message_templates, message_template
from slices.email_notifications.domain import NoEditableFields, NoValidRecipients
from slices.email_notifications.models import DeliveryResult, MessageTemplate, RenderedEmail, RenderedNotification
from slices.email_notifications.repository import (
    MongoMessageTemplateRepository, template_document, template_from_document,
)
from slices.email_notifications.service import EmailNotificationsService, TemplateNotFound
from slices.email_notifications.web import (
    EmailPreviewPayload, EmailTestSendPayload, NotificationPreviewPayload,
    email_notifications_http_error,
)


TEMPLATE = MessageTemplate("welcome", "user", "Hi {{name}}", "Body {{name}}", "Title", "Notice", "D")
HEADER = MessageTemplate("header", "layout", "", "Header")
FOOTER = MessageTemplate("footer", "layout", "", "Footer")


class FakeRepository:
    def __init__(self, templates=()):
        self.items = {item.key: item for item in templates}
        self.updated = None
        self.seeded = None

    async def get(self, key): return self.items.get(key)
    async def list(self): return list(self.items.values())
    async def update(self, key, fields):
        self.updated = (key, dict(fields))
        if key not in self.items: return None
        old = self.items[key]
        self.items[key] = MessageTemplate(
            old.key, old.category, str(fields.get("subject", old.subject)),
            str(fields.get("body_html", old.body_html)),
            str(fields.get("notification_title", old.notification_title)),
            str(fields.get("notification_body", old.notification_body)),
            str(fields.get("description", old.description)),
        )
        return self.items[key]
    async def upsert(self, template, timestamp):
        self.items[template.key] = template
        self.updated = (template.key, timestamp)
        return template
    async def seed(self, templates, timestamp): self.seeded = (tuple(templates), timestamp)


class FakeGateway:
    def __init__(self, result=DeliveryResult("success")):
        self.result = result
        self.calls = []
    async def send(self, recipient, subject, html):
        self.calls.append((recipient, subject, html))
        return self.result


def run(coroutine):
    return asyncio.run(coroutine)


def test_service_lists_gets_updates_resets_and_seeds_templates():
    repository = FakeRepository((TEMPLATE, HEADER, FOOTER, MessageTemplate("a", "layout", "", "")))
    service = EmailNotificationsService(repository, FakeGateway(), "https://app")
    assert [item.key for item in run(service.templates())] == ["a", "footer", "header", "welcome"]
    assert run(service.template("welcome")) == TEMPLATE
    updated = run(service.update("welcome", {"subject": "Changed", "key": "ignored"}, "now"))
    assert updated.subject == "Changed"
    assert repository.updated == ("welcome", {"subject": "Changed", "updated_at": "now"})
    default = MessageTemplate("welcome", "user", "Default", "Body")
    assert run(service.reset("welcome", {"welcome": default}, "later")) == default
    run(service.seed((default,), "seed-time"))
    assert repository.seeded == ((default,), "seed-time")
    with pytest.raises(TemplateNotFound): run(service.template("missing"))
    with pytest.raises(TemplateNotFound): run(service.update("missing", {"subject": "x"}, "now"))
    with pytest.raises(TemplateNotFound): run(service.reset("missing", {}, "now"))


def test_service_handles_update_race_and_empty_edit_payload():
    repository = FakeRepository((TEMPLATE,))
    service = EmailNotificationsService(repository, FakeGateway(), "")
    with pytest.raises(NoEditableFields): run(service.update("welcome", {"key": "x"}, "now"))
    original_update = repository.update
    async def vanished(key, fields): return None
    repository.update = vanished
    with pytest.raises(TemplateNotFound): run(service.update("welcome", {"subject": "x"}, "now"))
    repository.update = original_update


def test_service_renders_email_notification_and_missing_template_override():
    service = EmailNotificationsService(FakeRepository((TEMPLATE, HEADER, FOOTER)), FakeGateway(), "https://app")
    email = run(service.email("welcome", {"name": "Ada"}))
    assert email.subject == "Hi Ada" and "Header" in email.html and "Footer" in email.html
    notification = run(service.notification("welcome", {}))
    assert notification == RenderedNotification("Title", "Notice")
    override = run(service.email("missing", {}, "Subject", "Override"))
    assert override.subject == "Subject" and "Override" in override.html
    with pytest.raises(TemplateNotFound): run(service.email("missing", {}))


def test_service_sends_messages_and_test_recipient_batch():
    gateway = FakeGateway()
    service = EmailNotificationsService(FakeRepository((TEMPLATE,)), gateway, "")
    assert run(service.send("a@b.de", "S", "H")).status == "success"
    assert run(service.send_rendered("a@b.de", "welcome", {"name": "Ada"})).status == "success"
    missing = run(service.send_rendered("a@b.de", "missing", {}))
    assert missing == DeliveryResult("skipped", error="template 'missing' missing")
    recipients, results = run(service.send_test("a@b.de", ["B@b.de"], RenderedEmail("S", "H")))
    assert recipients == ("a@b.de", "B@b.de") and len(results) == 2


def test_models_serialize_only_present_optional_delivery_fields():
    assert RenderedEmail("S", "H").to_document() == {"subject": "S", "html": "H"}
    assert RenderedNotification("T", "B").to_document() == {"title": "T", "body": "B"}
    assert DeliveryResult("success").to_document() == {"status": "success"}
    assert DeliveryResult("failed", "message", "error").to_document() == {
        "status": "failed", "message": "message", "error": "error",
    }


def test_default_template_definitions_are_converted_to_typed_values():
    converted = message_template("x", {})
    assert converted == MessageTemplate("x", "user", "", "")
    defaults = default_message_templates()
    assert defaults["header"].category == "layout"
    assert defaults["user_password_reset"].subject


class AsyncCursor:
    def __init__(self, documents): self.documents = documents
    async def to_list(self, limit): return self.documents[:limit]


class Collection:
    def __init__(self, documents=()):
        self.documents = [dict(item) for item in documents]
        self.updates = []
        self.inserts = []
    async def find_one(self, query, *args):
        return next((item for item in self.documents if item.get("key") == query.get("key")), None)
    def find(self, *args): return AsyncCursor(self.documents)
    async def update_one(self, query, update, upsert=False): self.updates.append((query, update, upsert))
    async def insert_one(self, document): self.inserts.append(document)


class Database:
    def __init__(self, documents=()): self.email_templates = Collection(documents)


def test_mongo_repository_maps_crud_and_seed_paths():
    document = template_document(TEMPLATE)
    assert template_from_document({}) == MessageTemplate("", "user", "", "")
    assert template_from_document(document) == TEMPLATE
    database = Database(({**document, "updated_at": "now"},))
    repository = MongoMessageTemplateRepository(database)
    assert run(repository.get("welcome")) == TEMPLATE
    assert run(repository.get("missing")) is None
    assert run(repository.list()) == [TEMPLATE]
    assert run(repository.update("welcome", {"subject": "x"})) == TEMPLATE
    assert database.email_templates.updates[-1] == ({"key": "welcome"}, {"$set": {"subject": "x"}}, False)
    assert run(repository.upsert(TEMPLATE, "now")) == TEMPLATE
    run(repository.seed((TEMPLATE,), "now"))
    updates_after_complete_seed = len(database.email_templates.updates)
    assert updates_after_complete_seed == 2
    existing_missing_fields = {"key": "partial", "category": "user", "subject": "", "body_html": "B"}
    partial = MessageTemplate("partial", "user", "S", "B", description="D")
    database.email_templates.documents.append(existing_missing_fields)
    run(repository.seed((partial, MessageTemplate("new", "user", "S", "B")), "later"))
    assert database.email_templates.inserts[-1]["key"] == "new"


def test_web_payload_defaults_and_error_mapping():
    assert EmailPreviewPayload().variables is None
    assert NotificationPreviewPayload().title is None
    assert EmailTestSendPayload().recipients == []
    assert email_notifications_http_error(TemplateNotFound()).status_code == 404
    assert email_notifications_http_error(NoEditableFields()).detail == "No editable fields provided"
    assert email_notifications_http_error(NoValidRecipients()).detail == "No valid recipients"
    assert email_notifications_http_error(ValueError()).detail == "Invalid notification operation"


class SuccessfulSmtp:
    def __init__(self, *args, **kwargs): self.message = None
    def __enter__(self): return self
    def __exit__(self, *args): return None
    def starttls(self): pass
    def login(self, username, password): assert (username, password) == ("user", "pass")
    def send_message(self, message): self.message = message


def test_smtp_gateway_skips_unconfigured_and_sends_configured_message():
    assert SmtpEmailGateway("host", 25, "", "", "").send_sync("a@b.de", "S", "H").status == "skipped"
    gateway = SmtpEmailGateway("host", 25, "user", "pass", "from@b.de")
    with patch("infrastructure.smtp_email_gateway.smtplib.SMTP", SuccessfulSmtp):
        assert gateway.send_sync("a@b.de", "Subject", "<b>Body</b>") == DeliveryResult("success")


@pytest.mark.parametrize("error", [smtplib.SMTPException("smtp"), RuntimeError("other")])
def test_smtp_gateway_reports_expected_and_unexpected_failures(error):
    gateway = SmtpEmailGateway("host", 25, "user", "pass", "from@b.de")
    with patch("infrastructure.smtp_email_gateway.smtplib.SMTP", side_effect=error):
        result = gateway.send_sync("a@b.de", "S", "H")
    assert result.status == "failed" and result.error == str(error)


def test_smtp_async_send_delegates_to_sync_sender():
    gateway = SmtpEmailGateway("host", 25, "", "", "")
    assert run(gateway.send("a@b.de", "S", "H")).status == "skipped"
