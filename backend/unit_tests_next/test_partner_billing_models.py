"""Contract tests for immutable billing values and infrastructure mappers."""
import pytest

from slices.partner_billing.domain import billing_stats, create_usage_charge, resolve_price
from slices.partner_billing.mappers import (
    charge_from_document,
    document_id,
    partner_from_document,
    service_step_from_document,
    settings_from_document,
    upload_from_document,
    user_from_document,
)
from slices.partner_billing.models import (
    BillingSettings,
    BillingUser,
    ChargeStatus,
    Money,
    PartnerAccount,
    PriceSource,
    ServiceStep,
    UploadReference,
)


def test_money_normalizes_currency_and_rejects_invalid_values():
    assert Money(125, " EUR ") == Money(125, "eur")
    with pytest.raises(ValueError, match="negative"):
        Money(-1, "eur")
    with pytest.raises(ValueError, match="three-letter"):
        Money(1, "euro")


def test_document_mappers_isolate_mongo_shapes_and_defaults():
    assert document_id({"id": "public", "_id": "mongo"}) == "public"
    assert document_id({"_id": "mongo"}) == "mongo"
    assert document_id({}) == ""
    partner = partner_from_document({
        "_id": "p1", "name": None,
        "stripe_customer_id": "cus", "stripe_subscription_id": "sub",
        "billing_settings": {"default_currency": "usd"},
        "step_user_fee_cents": {"s1": 900},
    })
    assert partner == PartnerAccount(
        id="p1", stripe_customer_id="cus", stripe_subscription_id="sub",
        default_currency="usd", step_prices={"s1": 900},
    )
    assert partner_from_document({"id": "p2"}).default_currency == "eur"
    assert user_from_document({"_id": "u1", "name": None}) == BillingUser("u1")
    assert service_step_from_document(None) is None
    assert service_step_from_document({
        "_id": "s1", "title": None, "partner_user_fee_cents": 0,
    }) == ServiceStep("s1", fee_cents=0)
    assert upload_from_document({}) == UploadReference()
    assert upload_from_document({"file_id": "f1"}) == UploadReference("f1")
    assert settings_from_document({}) == BillingSettings()
    assert settings_from_document({
        "stripe_partner_user_fee_cents": "42",
        "stripe_partner_user_fee_currency": "chf",
    }) == BillingSettings(42, "chf")


def test_typed_price_charge_and_stats_contract():
    partner = PartnerAccount(
        id="p1", name="Partner", default_currency="usd",
        step_prices={"s1": 250},
    )
    step = ServiceStep("s1", "Sprachprüfung", 200)
    assert resolve_price(BillingSettings(100), None, partner) == (100, PriceSource.GLOBAL)
    assert resolve_price(BillingSettings(100), ServiceStep("s2", fee_cents=200), partner) == (
        200, PriceSource.STEP,
    )
    assert resolve_price(BillingSettings(100), step, partner) == (250, PriceSource.PARTNER_STEP)
    charge = create_usage_charge(
        partner, BillingUser("u1", "Ada"), UploadReference("f1"), step,
        BillingSettings(100), charge_id="c1", created_at="now",
    )
    assert charge.to_document() == {
        "id": "c1", "partner_id": "p1", "partner_name": "Partner",
        "user_id": "u1", "user_name": "Ada", "amount": 250,
        "currency": "usd", "status": "pending", "service_step_id": "s1",
        "service_step_title": "Sprachprüfung", "price_source": "partner_step",
        "first_upload_file_id": "f1", "created_at": "now",
    }
    billed = charge_from_document({**charge.to_document(), "id": "c2", "status": "billed", "amount": 300})
    stats = billing_stats([charge, billed])
    assert stats.to_dict()["pending"] == [charge.to_document()]
    assert (stats.pending_users, stats.pending_amount) == (1, 250)
    assert (stats.billed_users, stats.billed_amount, stats.currency) == (1, 300, "usd")
    assert billing_stats([]).to_dict() == {
        "pending_users": 0, "pending_amount": 0, "billed_users": 0,
        "billed_amount": 0, "currency": "eur", "pending": [],
    }


def test_charge_mapper_applies_ledger_defaults():
    charge = charge_from_document({"id": "c", "partner_id": 1, "user_id": 2})
    assert charge.status is ChargeStatus.PENDING
    assert charge.price_source is PriceSource.GLOBAL
    assert charge.money == Money(0, "eur")
    assert charge.to_document() == {
        "id": "c", "partner_id": "1", "partner_name": "",
        "user_id": "2", "user_name": "", "amount": 0, "currency": "eur",
        "status": "pending", "service_step_id": "", "service_step_title": "",
        "price_source": "global", "first_upload_file_id": None, "created_at": "",
    }
    assert charge_from_document({"partner_id": "p", "user_id": "u"}).id == ""
    assert charge_from_document({"_id": "mongo", "partner_id": "p", "user_id": "u"}).id == "mongo"


def test_charge_mapper_preserves_every_populated_ledger_field():
    document = {
        "id": 99,
        "partner_id": 10,
        "partner_name": "Partner",
        "user_id": 20,
        "user_name": "User",
        "amount": "123",
        "currency": "CHF",
        "status": "queued",
        "service_step_id": 30,
        "service_step_title": "Service",
        "price_source": "partner_step",
        "first_upload_file_id": "file-1",
        "created_at": 123456,
    }
    assert charge_from_document(document).to_document() == {
        "id": "99", "partner_id": "10", "partner_name": "Partner",
        "user_id": "20", "user_name": "User", "amount": 123, "currency": "chf",
        "status": "queued", "service_step_id": "30", "service_step_title": "Service",
        "price_source": "partner_step", "first_upload_file_id": "file-1",
        "created_at": "123456",
    }
