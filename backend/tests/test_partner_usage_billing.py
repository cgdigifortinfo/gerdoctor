import asyncio
from types import SimpleNamespace

from bson import ObjectId

try:
    import backend.server as server
except ModuleNotFoundError:
    import server


class Cursor:
    def __init__(self, rows):
        self.rows = list(rows)

    async def to_list(self, _limit):
        return list(self.rows)


class UsageCharges:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    async def find_one(self, query):
        return next((row for row in self.rows if all(row.get(key) == value for key, value in query.items())), None)

    async def insert_one(self, document):
        if any(row["partner_id"] == document["partner_id"] and row["user_id"] == document["user_id"] and row.get("service_step_id", "") == document.get("service_step_id", "") for row in self.rows):
            raise server.DuplicateKeyError("duplicate")
        self.rows.append(dict(document))

    async def update_one(self, query, update):
        row = await self.find_one({key: value for key, value in query.items() if not isinstance(value, dict)})
        if row:
            row.update(update.get("$set", {}))

    def find(self, query, _projection=None):
        def matches(row):
            for key, expected in query.items():
                if isinstance(expected, dict):
                    if "$exists" in expected and (key in row) != expected["$exists"]:
                        return False
                    if "$gt" in expected and not row.get(key, 0) > expected["$gt"]:
                        return False
                elif row.get(key) != expected:
                    return False
            return True
        return Cursor(row for row in self.rows if matches(row))


class SiteSettings:
    async def find_one(self, _query):
        return {"stripe_partner_user_fee_cents": 1250, "stripe_partner_user_fee_currency": "eur"}


def context(rows=None):
    usage = UsageCharges(rows)
    return SimpleNamespace(partner_usage_charges=usage, site_settings=SiteSettings()), usage


def entities(with_subscription=True):
    partner = {"_id": ObjectId(), "name": "Test Partner"}
    if with_subscription:
        partner.update({"stripe_customer_id": "cus_test", "stripe_subscription_id": "sub_test"})
    user = {"_id": ObjectId(), "name": "Dr. Beispiel"}
    return partner, user


def test_first_partner_upload_queues_exactly_one_fee(monkeypatch):
    fake_db, usage = context()
    calls = []

    async def create_item(*args):
        calls.append(args)
        return {"id": "ii_test"}

    monkeypatch.setattr(server, "db", fake_db)
    monkeypatch.setattr(server, "create_pending_invoice_item", create_item)
    partner, user = entities()
    asyncio.run(server._record_partner_user_charge(partner, user, {"file_id": "file-1"}))
    asyncio.run(server._record_partner_user_charge(partner, user, {"file_id": "file-2"}))

    assert len(usage.rows) == 1
    assert len(calls) == 1
    assert usage.rows[0]["amount"] == 1250
    assert usage.rows[0]["status"] == "queued"
    assert usage.rows[0]["stripe_invoice_item_id"] == "ii_test"


def test_upload_without_subscription_remains_visible_as_open(monkeypatch):
    fake_db, usage = context()
    monkeypatch.setattr(server, "db", fake_db)
    partner, user = entities(with_subscription=False)

    asyncio.run(server._record_partner_user_charge(partner, user, {"file_id": "file-1"}))
    stats = asyncio.run(server._usage_billing_stats(str(partner["_id"])))

    assert usage.rows[0]["status"] == "pending"
    assert "Abonnement fehlt" in usage.rows[0]["sync_error"]
    assert stats["pending_users"] == 1
    assert stats["pending_amount"] == 1250


def test_pending_fee_is_synced_after_subscription_is_available(monkeypatch):
    partner, user = entities()
    row = {
        "id": "charge-1", "partner_id": str(partner["_id"]), "user_id": str(user["_id"]),
        "user_name": user["name"], "amount": 1250, "currency": "eur", "status": "pending",
    }
    fake_db, usage = context([row])
    monkeypatch.setattr(server, "db", fake_db)

    async def create_item(*_args):
        return {"id": "ii_retried"}

    monkeypatch.setattr(server, "create_pending_invoice_item", create_item)
    assert asyncio.run(server._sync_pending_partner_usage_charges(partner)) == 1
    assert usage.rows[0]["status"] == "queued"
    assert usage.rows[0]["stripe_invoice_item_id"] == "ii_retried"


def test_billing_stats_separate_open_and_paid_users(monkeypatch):
    partner, _ = entities()
    partner_id = str(partner["_id"])
    fake_db, _ = context([
        {"partner_id": partner_id, "user_id": "u1", "amount": 1250, "currency": "eur", "status": "queued"},
        {"partner_id": partner_id, "user_id": "u2", "amount": 1250, "currency": "eur", "status": "billed"},
    ])
    monkeypatch.setattr(server, "db", fake_db)

    stats = asyncio.run(server._usage_billing_stats(partner_id))
    assert stats == {
        "pending_users": 1, "pending_amount": 1250,
        "billed_users": 1, "billed_amount": 1250,
        "currency": "eur", "pending": [fake_db.partner_usage_charges.rows[0]],
    }


def test_price_precedence_is_global_then_step_then_partner_step():
    partner, _ = entities()
    step = {"id": "step-1", "title": "Fachsprachenprüfung"}
    settings = {"stripe_partner_user_fee_cents": 1000}
    assert server._effective_partner_user_fee(settings, step, partner) == (1000, "global")
    step["partner_user_fee_cents"] = 1500
    assert server._effective_partner_user_fee(settings, step, partner) == (1500, "step")
    partner["step_user_fee_cents"] = {"step-1": 2200}
    assert server._effective_partner_user_fee(settings, step, partner) == (2200, "partner_step")
    partner["step_user_fee_cents"]["step-1"] = 0
    assert server._effective_partner_user_fee(settings, step, partner) == (0, "partner_step")


def test_same_user_can_be_charged_once_for_each_distinct_service_step(monkeypatch):
    fake_db, usage = context()
    monkeypatch.setattr(server, "db", fake_db)

    async def create_item(*_args):
        return {"id": f"ii-{len(usage.rows)}"}

    monkeypatch.setattr(server, "create_pending_invoice_item", create_item)
    partner, user = entities()
    asyncio.run(server._record_partner_user_charge(partner, user, {"file_id": "f1"}, {"id": "step-1", "title": "Leistung 1"}))
    asyncio.run(server._record_partner_user_charge(partner, user, {"file_id": "f2"}, {"id": "step-2", "title": "Leistung 2"}))
    asyncio.run(server._record_partner_user_charge(partner, user, {"file_id": "f3"}, {"id": "step-2", "title": "Leistung 2"}))
    assert len(usage.rows) == 2
    assert {row["service_step_id"] for row in usage.rows} == {"step-1", "step-2"}


def test_upload_action_resolves_nearest_selected_partner_step():
    partner, _ = entities()
    pid = str(partner["_id"])
    steps = [
        {"id": "choice-1", "order": 2, "step_type": "partner_selection"},
        {"id": "docs-1", "order": 3, "step_type": "milestone"},
        {"id": "choice-2", "order": 5, "step_type": "partner_selection"},
        {"id": "docs-2", "order": 6, "step_type": "milestone"},
    ]
    progress = [
        {"step_id": "choice-1", "data": {"selected_partner_id": pid}},
        {"step_id": "choice-2", "data": {"selected_partner_id": pid}},
    ]
    assert server._service_step_for_partner_action(steps, progress, steps[-1], partner)["id"] == "choice-2"


class Users:
    def __init__(self, user):
        self.user = user

    async def find_one(self, _query):
        return self.user


def test_stripe_connection_audit_proposes_unique_customer_and_subscription(monkeypatch):
    partner, _ = entities(with_subscription=False)
    partner.update({"user_id": str(ObjectId()), "registration_source": "self_service"})
    monkeypatch.setattr(server, "db", SimpleNamespace(users=Users({"email": "partner@example.test"})))

    async def customers(_email):
        return {"data": [{"id": "cus_unique", "email": "partner@example.test"}]}

    async def subscriptions(customer_id):
        assert customer_id == "cus_unique"
        return {"data": [{"id": "sub_unique", "customer": customer_id, "status": "active"}]}

    monkeypatch.setattr(server, "find_customers_by_email", customers)
    monkeypatch.setattr(server, "list_customer_subscriptions", subscriptions)
    report = asyncio.run(server._stripe_connection_report(partner))
    assert report["repairable"] is True
    assert report["proposed_customer_id"] == "cus_unique"
    assert report["proposed_subscription_id"] == "sub_unique"
    assert report["proposed_billing_status"] == "active"


def test_stripe_connection_audit_never_repairs_ambiguous_customer_match(monkeypatch):
    partner, _ = entities(with_subscription=False)
    partner["user_id"] = str(ObjectId())
    monkeypatch.setattr(server, "db", SimpleNamespace(users=Users({"email": "duplicate@example.test"})))

    async def customers(_email):
        return {"data": [{"id": "cus_first"}, {"id": "cus_second"}]}

    monkeypatch.setattr(server, "find_customers_by_email", customers)
    report = asyncio.run(server._stripe_connection_report(partner))
    assert report["repairable"] is False
    assert report["proposed_customer_id"] == ""
    assert any("Mehrdeutige Zuordnung" in issue for issue in report["issues"])
