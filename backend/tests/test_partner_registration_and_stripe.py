from uuid import uuid4
import os
import hashlib
import hmac
import json
import time

import requests
from pymongo import MongoClient


def test_partner_registration_is_pending_without_stripe(base_url):
    api = f"{base_url}/api"
    email = f"partner-self-{uuid4().hex[:10]}@example.com"
    config = requests.get(f"{api}/partner-registration/config", timeout=20)
    config.raise_for_status()
    assert config.json()["registration_enabled"] is True

    response = requests.post(f"{api}/partner-registration", json={
        "company_name": "E2E Partner GmbH", "contact_name": "Partner Test",
        "email": email, "password": "Partner123!", "country": "DE",
        "description": "Integrationstest",
    }, timeout=20)
    response.raise_for_status()
    body = response.json()
    assert body["status"] == "pending"
    assert body["user"]["role"] == "partner"
    assert body["user"]["partner_registration_status"] == "pending"
    partner_headers = {"Authorization": f"Bearer {body['user']['access_token']}"}
    visible = requests.get(f"{api}/partner/submissions", headers=partner_headers, timeout=20)
    assert visible.status_code == 403  # survey assignment remains a separate prerequisite
    payment_status = requests.get(f"{api}/partner-payment/status", headers=partner_headers, timeout=20)
    assert payment_status.status_code == 200
    assert payment_status.json() == {"billing_status": "pending", "access_unlocked": False}
    assert requests.get(f"{api}/partner-payment/settings", headers=partner_headers, timeout=20).status_code == 200
    assert requests.put(f"{api}/partner-payment/settings", headers=partner_headers, json={"legal_name": "E2E Partner GmbH", "country": "DE"}, timeout=20).status_code == 200
    assert requests.get(f"{api}/partner-payment/stripe-status", headers=partner_headers, timeout=20).status_code == 200
    assert requests.get(f"{api}/partner-payment/invoices", headers=partner_headers, timeout=20).json() == []
    assert requests.post(f"{api}/partner-payment/portal", headers=partner_headers, timeout=20).status_code == 400

    admin = requests.post(f"{api}/auth/login", json={"email": "admin@example.com", "password": "Admin123!"}, timeout=20)
    admin.raise_for_status()
    headers = {"Authorization": f"Bearer {admin.json()['access_token']}"}
    partners = requests.get(f"{api}/admin/partners", headers=headers, timeout=20)
    partners.raise_for_status()
    partner = next(p for p in partners.json() if p["id"] == body["partner_id"])
    assert partner["registration_status"] == "pending"
    assert partner["survey_ids"] == []
    assert partner["is_active"] is False

    requests.delete(f"{api}/admin/partners/{body['partner_id']}", headers=headers, timeout=20).raise_for_status()


def test_payment_checkout_and_webhook_report_missing_admin_configuration(base_url):
    api = f"{base_url}/api"
    mongo = MongoClient(os.environ.get("MONGO_URL", "mongodb://mongo:27017"))
    database = mongo[os.environ.get("DB_NAME", "test_database")]
    original = database.site_settings.find_one({"_key": "global"}) or {}
    email = f"partner-payment-config-{uuid4().hex[:10]}@example.com"
    response = requests.post(f"{api}/partner-registration", json={"company_name": "Payment Config GmbH", "contact_name": "Payment Test", "email": email, "password": "Partner123!", "country": "DE"}, timeout=20)
    response.raise_for_status()
    body = response.json()
    partner_headers = {"Authorization": f"Bearer {body['user']['access_token']}"}
    try:
        database.site_settings.update_one({"_key": "global"}, {"$unset": {"stripe_partner_price_id": "", "stripe_test_webhook_secret": ""}}, upsert=True)
        checkout = requests.post(f"{api}/partner-payment/checkout", headers=partner_headers, timeout=20)
        assert checkout.status_code == 503
        assert "Partnerpreis" in checkout.json()["detail"]
        webhook = requests.post(f"{api}/partner-payment/webhook", data=b"{}", headers={"Stripe-Signature": "t=1,v1=invalid"}, timeout=20)
        assert webhook.status_code == 503
    finally:
        database.site_settings.replace_one({"_key": "global"}, original, upsert=True)
        admin = requests.post(f"{api}/auth/login", json={"email": "admin@example.com", "password": "Admin123!"}, timeout=20).json()
        requests.delete(f"{api}/admin/partners/{body['partner_id']}", headers={"Authorization": f"Bearer {admin['access_token']}"}, timeout=20)
        mongo.close()


def test_public_settings_never_expose_stripe_secrets(base_url):
    payload = requests.get(f"{base_url}/api/settings/public", timeout=20).json()
    assert "stripe_test_secret_key" not in payload
    assert "stripe_live_secret_key" not in payload
    assert "stripe_test_webhook_secret" not in payload
    assert "stripe" in payload


def test_paid_invoice_marks_matching_usage_charge_as_billed(base_url):
    api = f"{base_url}/api"
    mongo = MongoClient(os.environ.get("MONGO_URL", "mongodb://mongo:27017"))
    database = mongo[os.environ.get("DB_NAME", "test_database")]
    original = database.site_settings.find_one({"_key": "global"}) or {}
    partner_id = database.partners.insert_one({
        "name": "Usage Webhook Test", "stripe_customer_id": "cus_usage_webhook_test",
    }).inserted_id
    charge_id = f"charge-{uuid4().hex}"
    database.partner_usage_charges.insert_one({
        "id": charge_id, "partner_id": str(partner_id), "user_id": f"user-{uuid4().hex}",
        "amount": 1250, "currency": "eur", "status": "queued",
    })
    secret = "whsec_usage_test"
    try:
        database.site_settings.update_one({"_key": "global"}, {"$set": {
            "stripe_sandbox_mode": True, "stripe_test_webhook_secret": secret,
        }}, upsert=True)
        payload = json.dumps({
            "type": "invoice.paid",
            "data": {"object": {
                "id": "in_usage_test", "number": "TEST-0001", "customer": "cus_usage_webhook_test",
                "lines": {"data": [{"metadata": {"usage_charge_id": charge_id}}]},
            }},
        }, separators=(",", ":")).encode()
        timestamp = str(int(time.time()))
        signature = hmac.new(secret.encode(), timestamp.encode() + b"." + payload, hashlib.sha256).hexdigest()
        response = requests.post(
            f"{api}/partner-payment/webhook", data=payload,
            headers={"Stripe-Signature": f"t={timestamp},v1={signature}", "Content-Type": "application/json"}, timeout=20,
        )
        response.raise_for_status()
        charge = database.partner_usage_charges.find_one({"id": charge_id})
        assert charge["status"] == "billed"
        assert charge["stripe_invoice_id"] == "in_usage_test"
        assert charge["invoice_number"] == "TEST-0001"
        assert charge.get("billed_at")
    finally:
        database.partner_usage_charges.delete_one({"id": charge_id})
        database.partners.delete_one({"_id": partner_id})
        database.site_settings.replace_one({"_key": "global"}, original, upsert=True)
        mongo.close()
