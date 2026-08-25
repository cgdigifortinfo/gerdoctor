"""Unit tests for partner-billing persistence and orchestration boundaries."""
import asyncio

import pytest
from pymongo.errors import DuplicateKeyError

from slices.partner_billing.mappers import charge_from_document
from slices.partner_billing.models import (
    BillingSettings, BillingUser, PartnerAccount, ServiceStep, UploadReference,
)
from slices.partner_billing.repository import DuplicateUsageCharge, PartnerBillingRepository
from slices.partner_billing.service import PartnerBillingService


class Cursor:
    def __init__(self, rows):
        self.rows = rows

    async def to_list(self, limit):
        assert limit == 10000
        return self.rows


class Collection:
    def __init__(self, *, one=None, rows=None, duplicate=False):
        self.one = one
        self.rows = rows or []
        self.duplicate = duplicate
        self.calls = []

    async def find_one(self, query):
        self.calls.append(("find_one", query))
        return self.one

    async def insert_one(self, document):
        self.calls.append(("insert_one", document))
        if self.duplicate:
            raise DuplicateKeyError("duplicate")

    def find(self, query, projection):
        self.calls.append(("find", query, projection))
        return Cursor(self.rows)

    async def update_one(self, query, update):
        self.calls.append(("update_one", query, update))


class Database:
    def __init__(self):
        self.site_settings = Collection(one=None)
        self.partner_usage_charges = Collection(rows=[{
            "id": "c", "partner_id": "p", "user_id": "u", "amount": 1,
            "currency": "eur", "status": "pending", "created_at": "now",
        }])


def run(awaitable):
    return asyncio.run(awaitable)


def test_repository_covers_queries_updates_defaults_and_duplicate_translation():
    database = Database()
    repository = PartnerBillingRepository(database)
    assert run(repository.global_settings()) == BillingSettings()
    assert run(repository.find_charge("p", "u", "")) is None
    charge = charge_from_document(database.partner_usage_charges.rows[0])
    run(repository.insert_charge(charge))
    assert run(repository.usage_rows("p")) == [charge]
    assert run(repository.pending_sync_rows("p")) == [charge]
    run(repository.mark_sync_error("c", "error"))
    run(repository.mark_queued("c", "ii", "now"))
    database.partner_usage_charges.duplicate = True
    with pytest.raises(DuplicateUsageCharge):
        run(repository.insert_charge(charge))


class Repository:
    def __init__(self, *, existing=None, duplicate_result=None, rows=None, amount=100):
        self.existing = existing
        self.duplicate_result = duplicate_result
        self.rows = rows or []
        self.amount = amount
        self.duplicate = duplicate_result is not None
        self.errors = []
        self.queued = []

    async def usage_rows(self, _partner_id):
        return self.rows

    async def find_charge(self, _partner_id, _user_id, _service_step_id):
        result, self.duplicate_result = self.duplicate_result, None
        return result or self.existing

    async def global_settings(self):
        return BillingSettings(default_fee_cents=self.amount)

    async def insert_charge(self, _charge):
        if self.duplicate:
            raise DuplicateUsageCharge

    async def mark_sync_error(self, charge_id, message):
        self.errors.append((charge_id, message))

    async def mark_queued(self, charge_id, item_id, queued_at):
        self.queued.append((charge_id, item_id, queued_at))

    async def pending_sync_rows(self, _partner_id):
        return self.rows


def service(repository, gateway=None):
    async def successful_gateway(*_args):
        return {"id": "ii_1"}

    return PartnerBillingService(
        repository, gateway or successful_gateway,
        id_factory=lambda: "c1", clock=lambda: "now",
    )


PARTNER = PartnerAccount(id="p1", name="P", stripe_customer_id="cus", stripe_subscription_id="sub")
USER = BillingUser(id="u1", name="U")
UPLOAD = UploadReference()


def test_service_stats_and_existing_or_racing_charge_are_idempotent():
    existing = charge_from_document({"id": "existing", "partner_id": "p1", "user_id": "u1", "amount": 5})
    assert run(service(Repository(rows=[existing])).stats("p"))["pending_amount"] == 5
    assert run(service(Repository(existing=existing)).record_upload(PARTNER, USER, UPLOAD)) is existing
    raced = charge_from_document({"id": "raced", "partner_id": "p1", "user_id": "u1"})
    assert run(service(Repository(duplicate_result=raced)).record_upload(PARTNER, USER, UPLOAD)) is raced


def test_service_duplicate_without_readback_returns_built_charge():
    repository = Repository(duplicate_result={})
    repository.duplicate = True
    charge = run(service(repository).record_upload(PARTNER, USER, UPLOAD))
    assert charge.id == "c1"


def test_service_keeps_unconfigured_or_unlinked_charges_pending():
    zero = Repository(amount=0)
    charge = run(service(zero).record_upload(PARTNER, USER, UPLOAD))
    assert zero.errors == [(charge.id, "Nutzergebühr nicht konfiguriert")]
    unlinked = Repository()
    charge = run(service(unlinked).record_upload(PartnerAccount(id="p1"), USER, UPLOAD))
    assert unlinked.errors == [(charge.id, "Stripe-Kunde oder Abonnement fehlt")]


def test_service_queues_new_and_pending_charges_and_counts_only_successes():
    new_repository = Repository()
    run(service(new_repository).record_upload(PARTNER, USER, UPLOAD, ServiceStep(id="s1")))
    assert new_repository.queued == [("c1", "ii_1", "now")]

    calls = []
    async def mixed_gateway(*args):
        calls.append(args)
        if len(calls) == 2:
            raise RuntimeError("stripe down")
        return {"id": "ii_ok"}

    rows = [
        charge_from_document({"id": "a", "partner_id": "p1", "user_id": "u1", "amount": 10}),
        charge_from_document({"id": "b", "partner_id": "p1", "user_id": "u2", "amount": 20, "currency": "usd"}),
    ]
    repository = Repository(rows=rows)
    assert run(service(repository, mixed_gateway).sync_pending(PARTNER)) == 1
    assert repository.queued == [("a", "ii_ok", "now")]
    assert repository.errors == [("b", "stripe down")]


def test_service_does_not_query_pending_rows_without_stripe_link():
    repository = Repository(rows=[{"id": "unused"}])
    assert run(service(repository).sync_pending(PartnerAccount(id="p1"))) == 0


def test_service_uses_http_style_error_detail_when_available():
    class GatewayError(Exception):
        detail = "invalid customer"

    async def failing_gateway(*_args):
        raise GatewayError

    repository = Repository()
    run(service(repository, failing_gateway).record_upload(PARTNER, USER, UPLOAD))
    assert repository.errors == [("c1", "invalid customer")]
