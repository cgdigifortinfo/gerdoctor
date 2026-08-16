"""Browser E2E coverage for login and password reset through the real dev proxy.

Unlike most UI suites, these tests deliberately do not install a Playwright API
route. Requests must travel from the browser to the frontend origin and through
CRACO's /api proxy, so a broken REACT_APP_BACKEND_URL is caught here.
"""
from __future__ import annotations

import os
from datetime import datetime
from urllib.parse import quote, urlsplit
from uuid import uuid4

import pytest
import requests
from playwright.sync_api import expect, sync_playwright
from pymongo import MongoClient

from e2e_screenshots import capture_page


BACKEND = (os.environ.get("E2E_BACKEND_URL") or "http://localhost:8001").rstrip("/")
FRONTEND = (
    os.environ.get("E2E_FRONTEND_URL")
    or os.environ.get("FRONTEND_URL")
    or "http://localhost:3001"
).rstrip("/")
API = f"{BACKEND}/api"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin123!"
INITIAL_PASSWORD = "Start123!"
RESET_PASSWORD = "NeuSicher123!"
SUITE = "auth-flows"


def _admin_token() -> str:
    response = requests.post(
        f"{API}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _assert_same_origin_api(response_url: str) -> None:
    frontend = urlsplit(FRONTEND)
    response = urlsplit(response_url)
    assert (response.scheme, response.netloc) == (frontend.scheme, frontend.netloc)
    assert response.path.startswith("/api/")


def _new_browser_page(playwright):
    browser = playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--host-resolver-rules=MAP localhost host.docker.internal",
        ],
    )
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    return browser, context, context.new_page()


@pytest.fixture()
def reset_user():
    token = _admin_token()
    email = f"e2e-passwort-reset-{uuid4().hex[:10]}@example.com"
    response = requests.post(
        f"{API}/admin/users",
        headers=_headers(token),
        json={
            "email": email,
            "name": "E2E Passwort Reset",
            "password": INITIAL_PASSWORD,
            "role": "user",
        },
        timeout=30,
    )
    response.raise_for_status()
    user_id = response.json()["id"]
    mongo = MongoClient(os.environ.get("MONGO_URL", "mongodb://mongo:27017"))
    database = mongo[os.environ.get("DB_NAME", "test_database")]

    try:
        yield {"email": email, "id": user_id, "database": database}
    finally:
        database.password_reset_tokens.delete_many({"user_id": user_id})
        requests.delete(
            f"{API}/admin/users/{user_id}",
            headers=_headers(token),
            timeout=30,
        )
        mongo.close()


def test_admin_login_uses_real_frontend_proxy():
    with sync_playwright() as playwright:
        browser, context, page = _new_browser_page(playwright)
        try:
            page.goto(f"{FRONTEND}/login", wait_until="networkidle")
            expect(page.locator('[data-testid="login-email-input"]')).to_be_visible()
            capture_page(page, SUITE, "01-admin-login")

            page.locator('[data-testid="login-email-input"]').fill(ADMIN_EMAIL)
            page.locator('[data-testid="login-password-input"]').fill(ADMIN_PASSWORD)
            with page.expect_response(
                lambda response: response.url.endswith("/api/auth/login")
            ) as login_response:
                page.locator('[data-testid="login-submit-btn"]').click()

            response = login_response.value
            assert response.status == 200
            _assert_same_origin_api(response.url)
            page.wait_for_url("**/admin", timeout=20000)
            expect(page.locator('[data-testid="admin-logout-btn"]')).to_be_visible(timeout=15000)
            capture_page(page, SUITE, "02-admin-login-erfolgreich")
        finally:
            context.close()
            browser.close()


def test_password_reset_from_request_to_new_login(reset_user):
    email = reset_user["email"]
    database = reset_user["database"]

    with sync_playwright() as playwright:
        browser, context, page = _new_browser_page(playwright)
        try:
            page.goto(f"{FRONTEND}/login", wait_until="networkidle")
            page.get_by_role("link", name="Passwort vergessen?").click()
            page.wait_for_url("**/forgot-password")
            expect(page.locator('[data-testid="forgot-email-input"]')).to_be_visible()
            capture_page(page, SUITE, "03-passwort-vergessen")

            page.locator('[data-testid="forgot-email-input"]').fill(email)
            with page.expect_response(
                lambda response: response.url.endswith("/api/auth/forgot-password")
            ) as forgot_response:
                page.locator('[data-testid="forgot-submit-btn"]').click()

            response = forgot_response.value
            assert response.status == 200
            _assert_same_origin_api(response.url)
            expect(page.locator('[data-testid="forgot-success"]')).to_be_visible()
            capture_page(page, SUITE, "04-reset-link-angefordert")

            token_doc = database.password_reset_tokens.find_one(
                {"user_id": reset_user["id"], "used": False},
                sort=[("_id", -1)],
            )
            assert token_doc and token_doc.get("token")
            assert isinstance(token_doc.get("expires_at"), datetime)

            reset_url = f"{FRONTEND}/reset-password?token={quote(token_doc['token'])}"
            page.goto(reset_url, wait_until="networkidle")
            expect(page.locator('[data-testid="reset-password-input"]')).to_be_visible()
            capture_page(page, SUITE, "05-neues-passwort")

            page.locator('[data-testid="reset-password-input"]').fill(RESET_PASSWORD)
            page.locator('[data-testid="reset-confirm-password-input"]').fill(RESET_PASSWORD)
            with page.expect_response(
                lambda response: response.url.endswith("/api/auth/reset-password")
            ) as reset_response:
                page.locator('[data-testid="reset-submit-btn"]').click()

            response = reset_response.value
            assert response.status == 200
            _assert_same_origin_api(response.url)
            page.wait_for_url("**/login?passwordReset=success", timeout=15000)
            expect(page.locator('[data-testid="login-reset-success"]')).to_be_visible()
            capture_page(page, SUITE, "06-passwort-geaendert")

            used_token = database.password_reset_tokens.find_one({"token": token_doc["token"]})
            assert used_token and used_token["used"] is True

            page.locator('[data-testid="login-email-input"]').fill(email)
            page.locator('[data-testid="login-password-input"]').fill(RESET_PASSWORD)
            with page.expect_response(
                lambda response: response.url.endswith("/api/auth/login")
            ) as login_response:
                page.locator('[data-testid="login-submit-btn"]').click()

            response = login_response.value
            assert response.status == 200
            _assert_same_origin_api(response.url)
            page.wait_for_url("**/dashboard", timeout=20000)
            expect(page.locator('[data-testid="logout-btn"]')).to_be_visible(timeout=15000)
            capture_page(page, SUITE, "07-login-mit-neuem-passwort")
        finally:
            context.close()
            browser.close()
