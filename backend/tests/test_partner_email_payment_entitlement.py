"""Regression coverage for payment-based partner email visibility."""

import asyncio

import server


NOTICE = "Bitte authorisieren Sie ihre Zahlung"


def test_unpaid_self_service_partner_gets_payment_notice(monkeypatch):
    async def permitted(_user, permission):
        return permission == "partner.users.email.view"

    monkeypatch.setattr(server, "has_permission", permitted)
    value = asyncio.run(server._partner_user_email_value(
        {"role": "partner"},
        {"registration_source": "self_service", "billing_status": "pending"},
        "candidate@example.test",
    ))
    assert value == NOTICE


def test_paid_self_service_partner_with_email_permission_sees_address(monkeypatch):
    async def permitted(_user, _permission):
        return True

    monkeypatch.setattr(server, "has_permission", permitted)
    for billing_status in ("paid", "active", "trialing"):
        value = asyncio.run(server._partner_user_email_value(
            {"role": "partner"},
            {"registration_source": "self_service", "billing_status": billing_status},
            "candidate@example.test",
        ))
        assert value == "candidate@example.test"


def test_group_or_user_deny_masks_email_even_after_payment(monkeypatch):
    async def denied(_user, _permission):
        return False

    monkeypatch.setattr(server, "has_permission", denied)
    value = asyncio.run(server._partner_user_email_value(
        {"role": "partner"},
        {"registration_source": "self_service", "billing_status": "paid"},
        "candidate@example.test",
    ))
    assert value == NOTICE


def test_non_self_service_partner_still_needs_email_permission(monkeypatch):
    allowed = False

    async def permission(_user, _permission):
        return allowed

    monkeypatch.setattr(server, "has_permission", permission)
    value = asyncio.run(server._partner_user_email_value(
        {"role": "partner"}, {"registration_source": "admin"}, "candidate@example.test",
    ))
    assert value == NOTICE
