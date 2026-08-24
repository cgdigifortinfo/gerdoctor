"""Browser regression: an empty-progress user remains impersonatable."""

import os
from uuid import uuid4

import requests
from bson import ObjectId
from playwright.sync_api import expect, sync_playwright
from pymongo import MongoClient

from e2e_screenshots import install_api_proxy


BACKEND = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
FRONTEND = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
API = f"{BACKEND}/api"


def test_admin_can_impersonate_empty_progress_user_with_stale_group():
    session = requests.Session()
    login = session.post(
        f"{API}/auth/login",
        json={"email": "admin@example.com", "password": "Admin123!"},
        timeout=20,
    )
    login.raise_for_status()
    session.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})
    groups = session.get(f"{API}/admin/permission-groups", timeout=20).json()
    partner_group_id = next(
        group["id"] for group in groups if group["is_system"] and group["role"] == "partner"
    )
    survey = next(
        item for item in session.get(f"{API}/admin/surveys", timeout=20).json()
        if item["slug"] == "aerzte"
    )
    email = f"empty-progress-browser-{uuid4().hex[:9]}@test.de"
    created = session.post(
        f"{API}/admin/users",
        json={
            "email": email,
            "password": "Test123!",
            "name": "Empty Progress Browser",
            "role": "user",
            "survey_id": survey["id"],
        },
        timeout=20,
    )
    created.raise_for_status()
    user_id = created.json()["id"]
    mongo = MongoClient(os.environ["MONGO_URL"])
    db = mongo[os.environ["DB_NAME"]]
    db.user_progress.delete_many({"user_id": user_id})
    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"role": "user", "group_ids": [partner_group_id]}},
    )

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--host-resolver-rules=MAP localhost host.docker.internal"],
            )
            context = browser.new_context(viewport={"width": 1500, "height": 1000})
            install_api_proxy(context, BACKEND)
            page = context.new_page()
            page.goto(f"{FRONTEND}/login", wait_until="networkidle")
            page.locator('[data-testid="login-email-input"]').fill("admin@example.com")
            page.locator('[data-testid="login-password-input"]').fill("Admin123!")
            page.locator('[data-testid="login-submit-btn"]').click()
            page.wait_for_url("**/admin**", timeout=20000)
            page.locator('[data-testid="admin-users-tab"]').click()
            page.locator('[data-testid="user-search-input"]').fill(email)
            impersonate = page.locator(f'[data-testid="impersonate-user-{user_id}"]')
            expect(impersonate).to_be_visible(timeout=20000)
            impersonate.click()

            page.wait_for_url("**/dashboard", timeout=20000)
            expect(page.get_by_text("Keine Berechtigung")).to_have_count(0)
            expect(page.locator('[data-testid="stop-impersonation-btn"]')).to_be_visible(timeout=20000)
            context.close()
            browser.close()
    finally:
        session.delete(f"{API}/admin/users/{user_id}", timeout=20)
        mongo.close()
