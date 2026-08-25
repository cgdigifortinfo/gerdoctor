import pytest

from slices.stripe_subscription.domain import (
    ForeignCheckoutSession, SubscriptionRuleError, billing_status_matches,
    checkout_subscription_link, connection_report, normalized_emails,
    partner_access_unlocked, repaired_subscription_link,
    subscription_candidates, subscription_webhook_action, unique_live_customers,
)
from slices.stripe_subscription.models import ConnectionReport, PartnerSubscription, SubscriptionLink


PARTNER = PartnerSubscription("p", "Partner", None, None, "cus-old", "sub-old", "pending", "self_service")


def test_email_customer_and_subscription_candidates_are_deterministic():
    assert normalized_emails([" A@Example.DE ", None, "a@example.de", " "]) == ("a@example.de",)
    assert unique_live_customers([
        {"id": "cus", "name": "old"}, {"id": "cus", "name": "new"},
        {"id": "deleted", "deleted": True}, {"name": "missing"},
    ]) == [{"id": "cus", "name": "new"}]
    assert [row["id"] for row in subscription_candidates([
        {"id": "cancel", "status": "canceled"}, {"id": "active", "status": "active"},
    ])] == ["active"]
    for status in ("active", "trialing", "past_due", "unpaid", "incomplete"):
        assert subscription_candidates([
            {"id": status, "status": status}, {"id": "paused", "status": "paused"},
        ]) == [{"id": status, "status": status}]
    assert [row["id"] for row in subscription_candidates([
        {"id": "cancel", "status": "canceled"}, {"id": "other", "status": "paused"},
    ])] == ["other"]
    assert subscription_candidates([]) == []


def test_connection_report_marks_status_drift_and_repairability():
    report = connection_report(
        PARTNER, ("mail@example.test",), ["issue", "issue"], {"id": "cus"},
        {"id": "sub", "status": "active"}, 1, 1,
    )
    assert report == ConnectionReport(
        "p", "Partner", ("mail@example.test",), "cus-old", "sub-old", "pending",
        ("issue", "Lokaler Zahlungsstatus passt nicht zum Stripe-Status „active“."),
        "cus", "sub", "active", True,
    )
    assert report.to_document()["emails"] == ["mail@example.test"]
    assert repaired_subscription_link(report) == SubscriptionLink("cus", "sub", "active")
    ambiguous = connection_report(PARTNER, (), [], {"id": "cus"}, {"id": "sub", "status": "trialing"}, 2, 1)
    assert ambiguous.repairable is False
    with pytest.raises(SubscriptionRuleError) as not_repairable: repaired_subscription_link(ambiguous)
    assert not_repairable.value.args == ("connection is not repairable",)
    unchanged = connection_report(
        PartnerSubscription("p", "P", None, None, "cus", "sub", "paid"), (), [],
        {"id": "cus"}, {"id": "sub", "status": "active"}, 0, 0,
    )
    assert unchanged.repairable is False and unchanged.issues == ()
    fallback = connection_report(PartnerSubscription("p", "P", None, None, None, None, None), (), [], None, None, 0, 0)
    assert fallback == ConnectionReport("p", "P", (), "", "", "", (), "", "", "pending", False)
    missing_remote_ids = connection_report(PARTNER, (), [], {}, {"status": "active"}, 0, 0)
    assert missing_remote_ids.proposed_customer_id == "" and missing_remote_ids.proposed_subscription_id == ""
    issue_only = connection_report(
        PartnerSubscription("p", "P", None, None, "cus", "sub", "active"), (), ["issue"],
        {"id": "cus"}, {"id": "sub", "status": "active"}, 0, 0,
    )
    assert issue_only.repairable is True
    customer_drift = connection_report(
        PartnerSubscription("p", "P", None, None, "old", "sub", "active"), (), [],
        {"id": "new"}, {"id": "sub", "status": "active"}, 0, 0,
    )
    subscription_drift = connection_report(
        PartnerSubscription("p", "P", None, None, "cus", "old", "active"), (), [],
        {"id": "cus"}, {"id": "new"}, 0, 0,
    )
    assert customer_drift.repairable is True and subscription_drift.repairable is True
    missing_local_customer = connection_report(
        PartnerSubscription("p", "P", None, None, None, "sub", "active"), (), [],
        {"id": "XXXX"}, {"id": "sub", "status": "active"}, 0, 0,
    )
    missing_local_subscription = connection_report(
        PartnerSubscription("p", "P", None, None, "cus", None, "active"), (), [],
        {"id": "cus"}, {"id": "XXXX", "status": "active"}, 0, 0,
    )
    assert missing_local_customer.repairable is True and missing_local_subscription.repairable is True
    too_many_subscriptions = connection_report(PARTNER, (), ["issue"], {"id": "cus"}, {"id": "sub"}, 1, 2)
    assert too_many_subscriptions.repairable is False


def test_checkout_link_and_access_rules_cover_all_states():
    with pytest.raises(ForeignCheckoutSession):
        checkout_subscription_link("p", {"client_reference_id": "other"})
    assert checkout_subscription_link("p", {"client_reference_id": "p", "payment_status": "open"}) is None
    object_link = checkout_subscription_link("p", {
        "client_reference_id": "p", "payment_status": "paid", "customer": "cus",
        "subscription": {"id": "sub"},
    })
    scalar_link = checkout_subscription_link("p", {
        "client_reference_id": "p", "payment_status": "paid", "customer": None,
        "subscription": "sub-2",
    })
    assert object_link == SubscriptionLink("cus", "sub", "paid")
    assert scalar_link == SubscriptionLink("", "sub-2", "paid")
    empty_link = checkout_subscription_link("p", {
        "client_reference_id": "p", "payment_status": "paid", "customer": "cus", "subscription": None,
    })
    assert empty_link == SubscriptionLink("cus", "", "paid")
    assert billing_status_matches("paid", "active") is True
    assert billing_status_matches("active", "active") is True
    assert billing_status_matches("trialing", "trialing") is True
    assert billing_status_matches("pending", "active") is False
    assert partner_access_unlocked("admin", None) is True
    assert partner_access_unlocked("self_service", "paid") is True
    assert partner_access_unlocked("self_service", "past_due") is False


@pytest.mark.parametrize("event_type,event_object,expected_fields,sync", [
    ("checkout.session.completed", {"payment_status": "paid", "customer": "cus", "subscription": "sub"}, {
        "billing_status": "paid", "access_unlocked": True, "stripe_customer_id": "cus",
        "stripe_subscription_id": "sub", "paid_at": "now",
    }, True),
    ("invoice.paid", {}, {"billing_status": "active", "access_unlocked": True}, False),
    ("customer.subscription.updated", {"status": "trialing"}, {"billing_status": "active", "access_unlocked": True}, False),
    ("customer.subscription.updated", {"status": "active"}, {"billing_status": "active", "access_unlocked": True}, False),
    ("invoice.payment_failed", {}, {"billing_status": "past_due", "access_unlocked": False}, False),
    ("customer.subscription.deleted", {}, {"billing_status": "cancelled", "access_unlocked": False}, False),
])
def test_subscription_webhook_actions_are_explicit(event_type, event_object, expected_fields, sync):
    action = subscription_webhook_action(event_type, event_object, "now")
    assert action.fields == expected_fields
    assert action.sync_pending_usage is sync


def test_subscription_webhook_ignores_irrelevant_or_non_active_events():
    assert subscription_webhook_action("checkout.session.completed", {"payment_status": "open"}, "now") is None
    assert subscription_webhook_action("customer.subscription.updated", {"status": "past_due"}, "now") is None
    assert subscription_webhook_action("unrelated", {}, "now") is None
