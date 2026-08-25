from __future__ import annotations

import asyncio
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest
from bson import ObjectId

from infrastructure import stripe_subscription_gateway as gateway_module
from slices.stripe_subscription.domain import ForeignCheckoutSession, MissingStripeCustomer, MissingSubscriptionPrice
from infrastructure.stripe_subscription_gateway import StripeApiSubscriptionGateway
from slices.stripe_subscription.models import CheckoutIdentity, CheckoutSettings, ConnectionReport, PartnerSubscription
from slices.stripe_subscription.administration import (
    MongoStripeConnectionAdministrationRepository,
    StripeConnectionAdministrationService,
    StripeConnectionInvalidPartnerId,
    StripeConnectionPartnerNotFound,
    subscription_partner,
)
from slices.stripe_subscription.partner_portal import (
    MongoPartnerPortalRepository,
    PartnerPortalNotLinked,
    PartnerPortalPartnerNotFound,
    PartnerPortalService,
)
from slices.stripe_subscription.repository import MongoStripeSubscriptionRepository
from slices.stripe_subscription.service import StripeSubscriptionService
from slices.stripe_subscription.web import stripe_subscription_http_error


PARTNER = PartnerSubscription("p", "Partner", "contact@example.test", None, None, None, "pending", "self_service")


class Repository:
    def __init__(self): self.email = "user@example.test"; self.calls = []
    async def user_email(self, partner): return self.email  # type: ignore[no-untyped-def]
    async def save_customer(self, partner_id, customer_id): self.calls.append(("customer", partner_id, customer_id))  # type: ignore[no-untyped-def]
    async def save_link(self, partner_id, link, timestamp, repaired=False): self.calls.append(("link", partner_id, link, timestamp, repaired))  # type: ignore[no-untyped-def]


class Gateway:
    def __init__(self):
        self.customer = {"id": "cus"}; self.customers = [{"id": "cus"}]
        self.subscription = {"id": "sub", "customer": "cus", "status": "active"}
        self.subscriptions = [self.subscription]; self.fail = set(); self.calls = []
        self.session = {"client_reference_id": "p", "payment_status": "paid", "customer": "cus", "subscription": "sub"}
    async def create_customer(self, *args): self.calls.append(("create_customer", *args)); return {"id": "cus"}
    async def create_checkout(self, *args): self.calls.append(("checkout", *args)); return {"url": "checkout"}
    async def checkout_session(self, session_id): return self.session
    async def create_portal(self, customer_id, return_url): return {"url": "portal"}
    async def retrieve_customer(self, customer_id):
        if "customer" in self.fail: raise RuntimeError
        return self.customer
    async def customers_by_email(self, email):
        if "search" in self.fail: raise RuntimeError
        return self.customers
    async def retrieve_subscription(self, subscription_id):
        if "subscription" in self.fail: raise RuntimeError
        return self.subscription
    async def subscriptions_for_customer(self, customer_id):
        if "subscriptions" in self.fail: raise RuntimeError
        return self.subscriptions


def service(repository=None, gateway=None):
    synced = []
    async def sync(partner_id): synced.append(partner_id); return 1
    return StripeSubscriptionService(repository or Repository(), gateway or Gateway(), sync), synced


def test_checkout_status_portal_and_repair_lifecycle():
    async def scenario():
        repository, gateway = Repository(), Gateway()
        subject, synced = service(repository, gateway)
        with pytest.raises(MissingSubscriptionPrice):
            await subject.checkout(PARTNER, CheckoutIdentity("u@x", "User"), CheckoutSettings(None), "ok", "cancel")
        assert await subject.checkout(PARTNER, CheckoutIdentity("u@x", "User"), CheckoutSettings("price", True, True), "ok", "cancel") == "checkout"
        linked = PartnerSubscription("p", "Partner", None, None, "existing", None, "trialing")
        assert await subject.checkout(linked, CheckoutIdentity("u@x", "User"), CheckoutSettings("price"), "ok", "cancel") == "checkout"
        assert await subject.checkout_status(PARTNER, None, "now") == "pending"
        assert await subject.checkout_status(PARTNER, "session", "now") == "paid"
        gateway.session = {"client_reference_id": "p", "payment_status": "open"}
        assert await subject.checkout_status(PARTNER, "session", "now") == "pending"
        with pytest.raises(MissingStripeCustomer): await subject.portal(PARTNER, "return")
        assert await subject.portal(linked, "return") == "portal"
        report = await subject.connection_report(PARTNER)
        assert report.repairable is True
        assert await subject.repair(PARTNER, report, "now") is True and synced == ["p"]
        assert await subject.repair(PARTNER, replace(report, repairable=False), "now") is False
    asyncio.run(scenario())


def test_connection_report_handles_deleted_ambiguous_foreign_and_gateway_failures():
    async def scenario():
        repository, gateway = Repository(), Gateway()
        subject, _ = service(repository, gateway)
        existing = PartnerSubscription("p", "P", None, None, "old", "old-sub", "active")
        gateway.customer = {"id": "old", "deleted": True}
        gateway.customers = [{"id": "one"}, {"id": "two"}, {"id": "two"}]
        report = await subject.connection_report(existing)
        assert any("gelöscht" in issue for issue in report.issues) and any("Mehrdeutige" in issue for issue in report.issues)
        gateway.customer = {"id": "cus"}; gateway.subscription = {"id": "sub", "customer": "foreign", "status": "active"}
        gateway.customers = [{"id": "cus"}]; gateway.subscriptions = []
        report = await subject.connection_report(existing)
        assert any("anderen Stripe-Kunden" in issue for issue in report.issues)
        discover_subscriptions = PartnerSubscription("p", "P", None, None, "cus", None, "active")
        gateway.customer = {"id": "cus"}; gateway.subscriptions = [
            {"id": "one", "customer": "cus", "status": "active"},
            {"id": "two", "customer": "cus", "status": "trialing"},
        ]
        report = await subject.connection_report(discover_subscriptions)
        assert any("2 Stripe-Abonnements" in issue for issue in report.issues)
        gateway.fail = {"subscriptions"}
        report = await subject.connection_report(discover_subscriptions)
        assert "Stripe-Abonnements konnten nicht geprüft werden." in report.issues
        gateway.fail = {"customer", "search", "subscription", "subscriptions"}
        report = await subject.connection_report(existing)
        assert any("ungültig" in issue for issue in report.issues)
        missing = PartnerSubscription("p", "P", None, None, None, None, None)
        report = await subject.connection_report(missing)
        assert "Stripe-Customer-ID fehlt." in report.issues
    asyncio.run(scenario())


class Collection:
    def __init__(self, row=None): self.row = row; self.calls = []
    async def find_one(self, query): self.calls.append(("find", query)); return self.row
    async def update_one(self, query, update): self.calls.append(("update", query, update))


def test_mongo_repository_maps_users_and_subscription_updates():
    async def scenario():
        partner_id, user_id = str(ObjectId()), str(ObjectId())
        database = SimpleNamespace(users=Collection({"email": "u@x"}), partners=Collection())
        repository = MongoStripeSubscriptionRepository(database)
        partner = PartnerSubscription(partner_id, "P", None, user_id, None, None, None)
        assert await repository.user_email(partner) == "u@x"
        database.users.row = None
        assert await repository.user_email(PartnerSubscription(partner_id, "P", None, None, None, None, None)) is None
        await repository.save_customer(partner_id, "cus"); await repository.save_customer("bad", "cus")
        from slices.stripe_subscription.models import SubscriptionLink
        await repository.save_link(partner_id, SubscriptionLink("cus", "sub", "active"), "now", True)
        await repository.save_link(partner_id, SubscriptionLink("cus", "sub", "past_due"), "later")
        await repository.save_link("bad", SubscriptionLink("", "", "pending"), "now")
        assert len(database.partners.calls) == 3
    asyncio.run(scenario())


def test_gateway_delegates_every_subscription_operation(monkeypatch):
    calls = []
    async def fake(*args, **kwargs): calls.append((args, kwargs)); return {"id": "x", "url": "url", "data": [{"id": "row"}]}
    for name in ("create_customer", "create_checkout_session", "checkout_session", "create_customer_portal", "retrieve_customer", "find_customers_by_email", "retrieve_subscription", "list_customer_subscriptions"):
        monkeypatch.setattr(gateway_module, name, fake)
    async def scenario():
        adapter = StripeApiSubscriptionGateway()
        await adapter.create_customer("e", "n", "p")
        await adapter.create_checkout("c", "price", "p", "ok", "cancel", True, False)
        await adapter.checkout_session("s"); await adapter.create_portal("c", "return")
        await adapter.retrieve_customer("c"); assert await adapter.customers_by_email("e") == [{"id": "row"}]
        await adapter.retrieve_subscription("s"); assert await adapter.subscriptions_for_customer("c") == [{"id": "row"}]
    asyncio.run(scenario()); assert len(calls) == 8


def test_web_errors_preserve_contract():
    errors = [MissingSubscriptionPrice(), MissingStripeCustomer(), ForeignCheckoutSession(), ValueError()]
    assert [stripe_subscription_http_error(error).status_code for error in errors] == [503, 400, 403, 400]


class ConnectionAdministrationRepository:
    def __init__(self):
        self.partners = [
            {"_id": "repair", "name": "Repair", "contact_email": "r@x.de"},
            {"_id": "skip", "name": "Skip"},
            {"_id": "clean", "name": "Clean"},
        ]

    async def self_service_partners(self): return self.partners
    async def partner(self, partner_id):
        return next((row for row in self.partners if row["_id"] == partner_id), None)


def connection_report_for(partner_id, repairable=False, issues=()):
    return ConnectionReport(
        partner_id, partner_id, (), "", "", "pending", tuple(issues),
        "customer", "subscription", "active", repairable,
    )


def test_stripe_connection_administration_audits_and_repairs_all_paths():
    class Subscriptions:
        async def connection_report(self, partner):
            if partner.id == "repair": return connection_report_for(partner.id, True, ("missing",))
            if partner.id == "skip": return connection_report_for(partner.id, False, ("ambiguous",))
            return connection_report_for(partner.id)

        async def repair(self, partner, report, timestamp):
            self.last_timestamp = timestamp
            return report.repairable

    repository = ConnectionAdministrationRepository()
    subscriptions = Subscriptions()
    subject = StripeConnectionAdministrationService(repository, subscriptions, lambda: "now")
    audit = asyncio.run(subject.audit())
    assert audit["defective"] == 2 and audit["repairable"] == 1
    repaired, skipped = asyncio.run(subject.repair_all())
    assert repaired == ["repair"] and skipped == ["skip"]
    assert asyncio.run(subject.repair("repair")).partner_id == "repair"
    assert asyncio.run(subject.repair("skip")) is None
    with pytest.raises(StripeConnectionPartnerNotFound): asyncio.run(subject.repair("missing"))
    mapped = subscription_partner({"_id": "p", "name": "P"})
    assert mapped.id == "p" and mapped.stripe_customer_id is None


def test_mongo_stripe_connection_administration_repository_validates_and_reads():
    class Cursor:
        def sort(self, *args): return self
        async def to_list(self, limit): return [{"_id": "p"}]

    class Partners:
        def find(self, query): return Cursor()
        async def find_one(self, query): return {"_id": str(query["_id"])}

    repository = MongoStripeConnectionAdministrationRepository(SimpleNamespace(partners=Partners()))
    assert asyncio.run(repository.self_service_partners()) == [{"_id": "p"}]
    with pytest.raises(StripeConnectionInvalidPartnerId): asyncio.run(repository.partner("bad"))
    valid = str(ObjectId())
    assert asyncio.run(repository.partner(valid))["_id"] == valid


class PortalRepository:
    def __init__(self):
        self.partner_row = {
            "_id": "p", "name": "P", "tags": ["tag"], "survey_ids": ["survey"],
            "billing_settings": {"city": "Berlin"}, "billing_status": "active",
            "registration_source": "self_service", "stripe_customer_id": "cus",
        }
        self.site = {
            "stripe_partner_price_id": "price", "stripe_partner_user_fee_cents": 100,
            "stripe_partner_user_fee_currency": "EUR", "stripe_automatic_tax": True,
            "stripe_allow_promotion_codes": True,
        }
        self.updated = None

    async def partner(self, partner_id): return self.partner_row if partner_id == "p" else None
    async def settings(self): return self.site
    async def service_steps(self, partner):
        return [{"_id": "step", "title": "Service", "order": 2, "partner_user_fee_cents": 200}]
    async def update_billing_settings(self, partner_id, fields): self.updated = (partner_id, dict(fields))


def test_partner_portal_service_covers_context_checkout_settings_and_views():
    class Subscriptions:
        async def checkout_status(self, partner, session_id, timestamp): return "active"
        async def checkout(self, partner, identity, settings, success, cancel):
            self.checkout_values = (partner, identity, settings, success, cancel); return "checkout"
        async def portal(self, partner, return_url): self.return_url = return_url; return "portal"

    repository, subscriptions = PortalRepository(), Subscriptions()
    async def usage(partner_id): return {"pending_users": 1}
    async def public(): return {"configured": True}
    async def invoices(customer_id): return [{"id": customer_id}]
    subject = PartnerPortalService(
        repository, subscriptions, usage, public, invoices, "https://portal.example/",
    )
    with pytest.raises(PartnerPortalNotLinked): asyncio.run(subject.own_partner({}))
    with pytest.raises(PartnerPortalPartnerNotFound): asyncio.run(subject.own_partner({"partner_id": "missing"}))
    partner = asyncio.run(subject.own_partner({"partner_id": "p"}))
    settings = asyncio.run(subject.settings(partner))
    assert settings["pricing"][0]["amount"] == 200 and settings["pricing"][0]["currency"] == "eur"
    assert asyncio.run(subject.status(partner, "session", "now"))["access_unlocked"] is True
    user = {"email": "u@x.de", "name": "User"}
    assert asyncio.run(subject.checkout(user, partner)) == "checkout"
    assert "CHECKOUT_SESSION_ID" in subscriptions.checkout_values[3]
    assert asyncio.run(subject.portal(partner)) == "portal"
    fields = asyncio.run(subject.update_settings("p", {"country": "DE", "default_currency": "EUR", "city": None}))
    assert fields == ["country", "default_currency"]
    assert repository.updated == ("p", {"country": "de", "default_currency": "eur"})
    assert asyncio.run(subject.stripe_status(partner))["customer_created"] is True
    assert asyncio.run(subject.invoices(partner)) == [{"id": "cus"}]
    assert asyncio.run(subject.invoices({})) == []


def test_mongo_partner_portal_repository_covers_queries_and_updates():
    valid = str(ObjectId())

    class Cursor:
        def __init__(self, rows): self.rows = rows
        def sort(self, *args): return self
        async def to_list(self, limit): return self.rows

    class Collection:
        def __init__(self, row=None): self.row = row; self.calls = []
        async def find_one(self, query): self.calls.append(("find_one", query)); return self.row
        def find(self, query): self.calls.append(("find", query)); return Cursor([{"_id": "step"}])
        async def update_one(self, *args): self.calls.append(("update", args))

    partners = Collection({"_id": valid})
    settings = Collection(None)
    steps = Collection()
    repository = MongoPartnerPortalRepository(SimpleNamespace(
        partners=partners, site_settings=settings, steps=steps,
    ))
    assert asyncio.run(repository.partner("bad")) is None
    assert asyncio.run(repository.partner(valid))["_id"] == valid
    assert asyncio.run(repository.settings()) == {}
    assert asyncio.run(repository.service_steps({"tags": []})) == [{"_id": "step"}]
    assert asyncio.run(repository.service_steps({"tags": ["x"], "survey_ids": ["s"]}))
    asyncio.run(repository.update_billing_settings("bad", {"city": "X"}))
    asyncio.run(repository.update_billing_settings(valid, {"city": "X"}))
    assert partners.calls[-1][0] == "update"
