from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest
from bson import ObjectId

from infrastructure.stripe_webhook import (
    StripeWebhookConfigurationError,
    StripeWebhookSignatureError,
    verified_stripe_event,
)
from slices.stripe_subscription.webhook import (
    MongoStripeWebhookRepository,
    StripeWebhookService,
)


def signature(body: bytes, secret: str, timestamp: int = 1000) -> str:
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def test_stripe_webhook_verifier_handles_configuration_timestamp_digest_and_payload():
    body = json.dumps({"type": "test"}).encode()
    with pytest.raises(StripeWebhookConfigurationError):
        verified_stripe_event(body, "", "", lambda: 1000)
    for invalid in ("", "t=x,v1=y", "t=1,v1=y", "t=1000,v1=wrong"):
        with pytest.raises(StripeWebhookSignatureError):
            verified_stripe_event(body, invalid, "secret", lambda: 1000)
    assert verified_stripe_event(body, signature(body, "secret"), "secret", lambda: 1000)["type"] == "test"
    assert verified_stripe_event(body, signature(body, "secret", 700), "secret", lambda: 1000)["type"] == "test"
    for invalid in (
        signature(body, "secret", 699),
        "v1=wrong",
        "t=1000",
        "ignored,t=1000,v1=wrong",
        "t=1000,v1=wrong=extra",
    ):
        with pytest.raises(StripeWebhookSignatureError):
            verified_stripe_event(body, invalid, "secret", lambda: 1000)
    scalar = b"[]"
    with pytest.raises(StripeWebhookSignatureError):
        verified_stripe_event(scalar, signature(scalar, "secret"), "secret", lambda: 1000)


class Repository:
    def __init__(self): self.charges = []; self.partners = []; self.site = {"stripe_test_webhook_secret": "secret"}
    async def settings(self): return self.site
    async def update_charge(self, charge_id, fields): self.charges.append((charge_id, dict(fields)))
    async def update_partner(self, partner_id, customer_id, fields):
        self.partners.append((partner_id, customer_id, dict(fields))); return {"_id": "p"}


def webhook_body(event_type, obj):
    return json.dumps({"type": event_type, "data": {"object": obj}}).encode()


def test_stripe_webhook_service_updates_direct_and_parent_invoice_metadata_and_subscription():
    repository, synced = Repository(), []
    async def sync(partner): synced.append(partner); return 1
    service = StripeWebhookService(repository, sync, lambda: "now", lambda: 1000)
    obj = {
        "id": "invoice", "number": "INV", "customer": "cus",
        "lines": {"data": [
            {"metadata": {"usage_charge_id": "direct"}},
            {"parent": {"invoice_item_details": {"metadata": {"usage_charge_id": "parent"}}}},
            {"metadata": {}},
        ]},
    }
    body = webhook_body("invoice.paid", obj)
    asyncio.run(service.handle(body, signature(body, "secret")))
    assert [row[0] for row in repository.charges] == ["direct", "parent"]
    assert repository.charges[0][1]["status"] == "billed"
    body = webhook_body("invoice.created", obj)
    asyncio.run(service.handle(body, signature(body, "secret")))
    assert "status" not in repository.charges[-1][1]
    checkout = {
        "client_reference_id": "507f1f77bcf86cd799439011", "customer": "cus",
        "subscription": "sub", "payment_status": "paid", "metadata": {},
    }
    body = webhook_body("checkout.session.completed", checkout)
    asyncio.run(service.handle(body, signature(body, "secret")))
    assert repository.partners[-1][0] == checkout["client_reference_id"] and synced
    body = webhook_body("unhandled", {})
    asyncio.run(service.handle(body, signature(body, "secret")))


def test_stripe_webhook_service_uses_live_secret_and_skips_sync_without_partner():
    repository = Repository()
    repository.site = {"stripe_sandbox_mode": False, "stripe_live_webhook_secret": "live"}
    async def sync(partner): raise AssertionError
    async def no_partner(partner_id, customer_id, fields): return None
    repository.update_partner = no_partner
    service = StripeWebhookService(repository, sync, lambda: "now", lambda: 1000)
    obj = {"customer": "cus", "subscription": "sub", "status": "active", "metadata": {}}
    body = webhook_body("customer.subscription.updated", obj)
    asyncio.run(service.handle(body, signature(body, "live")))


class Collection:
    def __init__(self, row=None): self.row = row; self.calls = []
    async def find_one(self, query): self.calls.append(("find", query)); return self.row
    async def update_one(self, *args): self.calls.append(("update", args))


def test_mongo_stripe_webhook_repository_all_persistence_paths():
    valid = str(ObjectId())
    settings = Collection(None); charges = Collection(); partners = Collection({"_id": valid})
    repository = MongoStripeWebhookRepository(SimpleNamespace(
        site_settings=settings, partner_usage_charges=charges, partners=partners,
    ))
    assert asyncio.run(repository.settings()) == {}
    asyncio.run(repository.update_charge("charge", {"status": "billed"}))
    assert asyncio.run(repository.update_partner(valid, "cus", {"billing_status": "active"})) == {"_id": valid}
    asyncio.run(repository.update_partner(None, "cus", {"billing_status": "past_due"}))
    assert partners.calls[-2][1][0] == {"stripe_customer_id": "cus"}
