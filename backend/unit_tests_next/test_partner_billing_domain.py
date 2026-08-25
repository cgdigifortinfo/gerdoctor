"""Exhaustive branch tests for the pure partner-billing rules."""
from bson import ObjectId

from slices.partner_billing.domain import (
    build_usage_charge,
    effective_partner_user_fee,
    invoice_item_description,
    invoice_item_metadata,
    pending_sync_error,
    service_step_for_partner_action,
    usage_billing_stats,
)


def test_usage_stats_split_billed_and_open_rows_and_use_latest_currency():
    pending = {"status": "queued", "amount": "100", "currency": "usd"}
    billed = {"status": "billed", "amount": 250, "currency": "eur"}
    no_amount = {"status": "pending"}
    assert usage_billing_stats([pending, billed, no_amount]) == {
        "pending_users": 2,
        "pending_amount": 100,
        "billed_users": 1,
        "billed_amount": 250,
        "currency": "eur",
        "pending": [pending, no_amount],
    }
    assert usage_billing_stats([])["currency"] == "eur"
    assert usage_billing_stats([
        {"status": "billed"},
        {"status": "pending", "currency": "gbp"},
    ]) == {
        "pending_users": 1, "pending_amount": 0,
        "billed_users": 1, "billed_amount": 0,
        "currency": "gbp",
        "pending": [{"status": "pending", "currency": "gbp"}],
    }


def test_price_precedence_includes_zero_and_object_id_steps():
    step_id = ObjectId()
    settings = {"stripe_partner_user_fee_cents": "100"}
    partner = {"step_user_fee_cents": {str(step_id): 0}}
    assert effective_partner_user_fee(settings, None, {}) == (100, "global")
    assert effective_partner_user_fee(settings, {"id": "s", "partner_user_fee_cents": 200}, {}) == (200, "step")
    assert effective_partner_user_fee(settings, {"_id": step_id}, partner) == (0, "partner_step")
    assert effective_partner_user_fee({}, None, {"step_user_fee_cents": {"": 999}}) == (0, "global")
    assert effective_partner_user_fee({}, None, {"step_user_fee_cents": {"XXXX": 999}}) == (0, "global")
    assert effective_partner_user_fee(
        settings, {"id": "plain-id"}, {"step_user_fee_cents": {"plain-id": 300}}
    ) == (300, "partner_step")


def test_service_step_resolution_supports_single_multi_and_legacy_name_selection():
    partner = {"_id": "p1", "name": "Partner Eins"}
    steps = [
        {"id": "ignored-type", "order": 1, "step_type": "text"},
        {"id": "single", "order": 2, "step_type": "partner_selection"},
        {"id": "multi", "order": 4, "step_type": "partner_multiselection"},
        {"id": "legacy", "order": 5, "step_type": "partner_selection"},
        {"id": "future", "order": 9, "step_type": "partner_selection"},
    ]
    progress = [
        {"step_id": "single", "data": {"selected_partner_id": "p1"}},
        {"step_id": "multi", "data": {"selected_partner_ids": ["p0", "p1"]}},
        {"step_id": "legacy", "data": {"selected_partner_name": "Partner Eins"}},
        {"step_id": "future", "data": {"selected_partner_id": "p1"}},
    ]
    assert service_step_for_partner_action(steps, progress, {"order": 6}, partner)["id"] == "legacy"
    assert service_step_for_partner_action(steps, [], {"order": 6}, partner) is None
    assert service_step_for_partner_action(
        [{"id": "legacy", "order": 1, "step_type": "partner_selection"}],
        [{"step_id": "legacy", "data": {"selected_partner_name": ""}}],
        {"order": 2}, {"_id": "p1", "name": ""},
    ) is None


def test_service_step_resolution_tests_each_selection_contract_independently():
    partner = {"_id": "target", "name": "Legacy Name"}
    action = {"order": 10}
    single = {"id": "single", "order": 1, "step_type": "partner_selection"}
    multi = {"id": "multi", "order": 2, "step_type": "partner_multiselection"}
    legacy = {"id": "legacy", "order": 3, "step_type": "partner_selection"}
    assert service_step_for_partner_action(
        [single], [{"step_id": "single", "data": {"selected_partner_id": "target"}}],
        action, partner,
    ) == single
    assert service_step_for_partner_action(
        [multi], [{"step_id": "multi", "data": {"selected_partner_ids": ["other", "target"]}}],
        action, partner,
    ) == multi
    assert service_step_for_partner_action(
        [legacy], [{"step_id": "legacy", "data": {"selected_partner_name": "Legacy Name"}}],
        action, partner,
    ) == legacy
    assert service_step_for_partner_action(
        [single], [{"step_id": "wrong-key", "data": {"selected_partner_id": "target"}}],
        action, partner,
    ) is None
    assert service_step_for_partner_action(
        [{**single, "order": 11}],
        [{"step_id": "single", "data": {"selected_partner_id": "target"}}],
        action, partner,
    ) is None
    same_order = {**single, "order": 10}
    assert service_step_for_partner_action(
        [same_order],
        [{"step_id": "single", "data": {"selected_partner_id": "target"}}],
        action, partner,
    ) == same_order
    missing_order = {"id": "missing-order", "step_type": "partner_selection"}
    assert service_step_for_partner_action(
        [missing_order],
        [{"step_id": "missing-order", "data": {"selected_partner_id": "target"}}],
        action, partner,
    ) == missing_order
    assert service_step_for_partner_action(
        [{**single, "order": 11}, single],
        [{"step_id": "single", "data": {"selected_partner_id": "target"}}],
        action, partner,
    ) == single
    assert service_step_for_partner_action(
        [legacy],
        [{"step_id": "legacy", "data": {"selected_partner_name": "XXXX"}}],
        action, {"_id": "target"},
    ) is None
    explicit_half = {"id": "half", "order": 0.5, "step_type": "partner_selection"}
    assert service_step_for_partner_action(
        [missing_order, explicit_half],
        [
            {"step_id": "missing-order", "data": {"selected_partner_id": "target"}},
            {"step_id": "half", "data": {"selected_partner_id": "target"}},
        ],
        action, partner,
    ) == explicit_half
    assert service_step_for_partner_action(
        [single],
        [{"step_id": "single", "data": {"selected_partner_id": "target"}}],
        {}, partner,
    ) is None
    assert service_step_for_partner_action(
        [missing_order],
        [{"step_id": "missing-order", "data": {"selected_partner_id": "target"}}],
        {"order": 0.5}, partner,
    ) == missing_order


def test_charge_document_uses_resolved_price_and_currency_fallbacks():
    partner = {"_id": "p1", "name": "P", "billing_settings": {"default_currency": "USD"}}
    user = {"_id": "u1", "name": "U"}
    charge = build_usage_charge(
        partner, user, {"file_id": "f1"},
        {"id": "s1", "title": "Service", "partner_user_fee_cents": 1200},
        {}, charge_id="c1", created_at="now",
    )
    assert charge == {
        "id": "c1", "partner_id": "p1", "partner_name": "P",
        "user_id": "u1", "user_name": "U", "amount": 1200,
        "currency": "usd", "status": "pending", "service_step_id": "s1",
        "service_step_title": "Service", "price_source": "step",
        "first_upload_file_id": "f1", "created_at": "now",
    }
    minimal = build_usage_charge(
        {"_id": "p"}, {"_id": "u"}, {}, None, {},
        charge_id="c", created_at="t",
    )
    assert minimal["currency"] == "eur"
    assert minimal["service_step_id"] == ""
    assert minimal["service_step_title"] == ""
    configured = build_usage_charge(
        {"_id": "partner", "billing_settings": {"default_currency": "usd"}},
        {"_id": "user"}, {"file_id": "upload"},
        {"_id": ObjectId(), "title": "Object-ID Service"},
        {"stripe_partner_user_fee_currency": "CHF"},
        charge_id="charge", created_at="timestamp",
    )
    assert configured["partner_name"] == ""
    assert configured["user_name"] == ""
    assert configured["currency"] == "chf"
    assert configured["service_step_id"] != ""
    assert configured["service_step_title"] == "Object-ID Service"
    assert configured["first_upload_file_id"] == "upload"


def test_pending_sync_reason_distinguishes_price_connection_and_ready_state():
    assert pending_sync_error(0, "customer", "subscription") == "Nutzergebühr nicht konfiguriert"
    assert pending_sync_error(1, None, "subscription") == "Stripe-Kunde oder Abonnement fehlt"
    assert pending_sync_error(1, "customer", None) == "Stripe-Kunde oder Abonnement fehlt"
    assert pending_sync_error(1, "customer", "subscription") is None


def test_invoice_item_helpers_use_user_fallback_and_stable_metadata():
    assert invoice_item_description("Ada", "u1") == "Nutzergebühr – Ada"
    assert invoice_item_description("", "u1") == "Nutzergebühr – u1"
    assert invoice_item_metadata({
        "id": "c1", "partner_id": "p1", "user_id": "u1",
    }) == {
        "partner_id": "p1", "user_id": "u1", "service_step_id": "",
        "usage_charge_id": "c1",
    }
    assert invoice_item_metadata({
        "id": "c2", "partner_id": "p2", "user_id": "u2",
        "service_step_id": "service-2",
    })["service_step_id"] == "service-2"
