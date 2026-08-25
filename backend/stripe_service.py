"""Minimal async Stripe Connect client.

The app stores only platform API configuration and connected-account IDs.
Identity, payout and bank details remain on Stripe-hosted pages.
"""
from __future__ import annotations

import os
from urllib.parse import quote
from typing import Any, cast

import httpx
from fastapi import HTTPException

from database import db


STRIPE_API = "https://api.stripe.com/v1"
SECRET_FIELDS = {
    "stripe_test_secret_key", "stripe_test_webhook_secret",
    "stripe_live_secret_key", "stripe_live_webhook_secret",
}


async def stripe_config() -> dict[str, Any]:
    settings: dict[str, Any] = cast(dict[str, Any] | None, await db.site_settings.find_one({"_key": "global"})) or {}
    sandbox = settings.get("stripe_sandbox_mode", True)
    prefix = "test" if sandbox else "live"
    secret = os.environ.get(f"STRIPE_{prefix.upper()}_SECRET_KEY") or settings.get(f"stripe_{prefix}_secret_key", "")
    publishable = os.environ.get(f"STRIPE_{prefix.upper()}_PUBLISHABLE_KEY") or settings.get(f"stripe_{prefix}_publishable_key", "")
    return {"sandbox_mode": sandbox, "secret_key": secret, "publishable_key": publishable, "configured": bool(secret)}


async def public_stripe_status() -> dict[str, Any]:
    cfg = await stripe_config()
    return {
        "configured": cfg["configured"],
        "sandbox_mode": cfg["sandbox_mode"],
        "publishable_key": cfg["publishable_key"],
    }


async def stripe_request(method: str, path: str, *, data: dict[str, Any] | None = None, account_id: str | None = None) -> dict[str, Any]:
    cfg = await stripe_config()
    if not cfg["configured"]:
        raise HTTPException(status_code=503, detail="Stripe ist noch nicht konfiguriert")
    headers = {"Authorization": f"Bearer {cfg['secret_key']}"}
    if account_id:
        headers["Stripe-Account"] = account_id
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.request(method, f"{STRIPE_API}{path}", data=data, headers=headers)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Stripe ist nicht erreichbar: {exc}") from exc
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if response.is_error:
        message = payload.get("error", {}).get("message") or "Stripe-Anfrage fehlgeschlagen"
        raise HTTPException(status_code=502, detail=message)
    return cast(dict[str, Any], payload)


async def create_connected_account(email: str, country: str = "DE") -> dict[str, Any]:
    return await stripe_request("POST", "/accounts", data={
        "type": "express",
        "country": country.upper(),
        "email": email,
        "business_type": "company",
        "capabilities[transfers][requested]": "true",
    })


async def connected_account(account_id: str) -> dict[str, Any]:
    return await stripe_request("GET", f"/accounts/{account_id}")


async def create_account_link(account_id: str, refresh_url: str, return_url: str) -> dict[str, Any]:
    return await stripe_request("POST", "/account_links", data={
        "account": account_id,
        "refresh_url": refresh_url,
        "return_url": return_url,
        "type": "account_onboarding",
        "collection_options[fields]": "eventually_due",
    })


async def create_dashboard_link(account_id: str) -> dict[str, Any]:
    return await stripe_request("POST", f"/accounts/{account_id}/login_links")


async def list_invoices(account_id: str) -> dict[str, Any]:
    return await stripe_request("GET", "/invoices?limit=100", account_id=account_id)


async def create_customer(email: str, name: str, partner_id: str) -> dict[str, Any]:
    return await stripe_request("POST", "/customers", data={
        "email": email, "name": name, "metadata[partner_id]": partner_id,
    })


async def create_checkout_session(customer_id: str, price_id: str, partner_id: str, success_url: str, cancel_url: str, mode: str = "subscription", automatic_tax: bool = False, promotion_codes: bool = False) -> dict[str, Any]:
    data = {
        "customer": customer_id, "mode": mode, "line_items[0][price]": price_id,
        "line_items[0][quantity]": "1", "success_url": success_url, "cancel_url": cancel_url,
        "client_reference_id": partner_id, "metadata[partner_id]": partner_id,
        "allow_promotion_codes": str(promotion_codes).lower(),
    }
    if automatic_tax:
        data["automatic_tax[enabled]"] = "true"
    if mode == "subscription":
        data["subscription_data[metadata][partner_id]"] = partner_id
    return await stripe_request("POST", "/checkout/sessions", data=data)


async def checkout_session(session_id: str) -> dict[str, Any]:
    return await stripe_request("GET", f"/checkout/sessions/{session_id}?expand[]=subscription")


async def create_customer_portal(customer_id: str, return_url: str) -> dict[str, Any]:
    return await stripe_request("POST", "/billing_portal/sessions", data={"customer": customer_id, "return_url": return_url})


async def list_customer_invoices(customer_id: str) -> dict[str, Any]:
    return await stripe_request("GET", f"/invoices?limit=100&customer={customer_id}")


async def retrieve_customer(customer_id: str) -> dict[str, Any]:
    return await stripe_request("GET", f"/customers/{customer_id}")


async def find_customers_by_email(email: str) -> dict[str, Any]:
    return await stripe_request("GET", f"/customers?limit=100&email={quote(email)}")


async def retrieve_subscription(subscription_id: str) -> dict[str, Any]:
    return await stripe_request("GET", f"/subscriptions/{subscription_id}")


async def list_customer_subscriptions(customer_id: str) -> dict[str, Any]:
    return await stripe_request("GET", f"/subscriptions?limit=100&status=all&customer={customer_id}")


async def create_pending_invoice_item(customer_id: str, subscription_id: str, amount: int, currency: str, description: str, metadata: dict[str, str]) -> dict[str, Any]:
    data = {
        "customer": customer_id,
        "subscription": subscription_id,
        "amount": str(amount),
        "currency": currency.lower(),
        "description": description,
    }
    for key, value in metadata.items():
        data[f"metadata[{key}]"] = value
    return await stripe_request("POST", "/invoiceitems", data=data)
