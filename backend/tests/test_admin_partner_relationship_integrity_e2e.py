"""Admin UI regression for orphan warnings and alphabetical partner choices."""

import os
from uuid import uuid4

import requests
from playwright.sync_api import expect, sync_playwright

from e2e_screenshots import install_api_proxy


BACKEND = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
FRONTEND = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
API = f"{BACKEND}/api"


def test_admin_marks_orphans_and_sorts_partner_user_choices():
    session = requests.Session()
    login = session.post(
        f"{API}/auth/login",
        json={"email": "admin@example.com", "password": "Admin123!"},
        timeout=20,
    )
    login.raise_for_status()
    session.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})
    survey = next(
        item for item in session.get(f"{API}/admin/surveys", timeout=20).json()
        if item["slug"] == "aerzte"
    )
    partner_step = next(
        item for item in session.get(f"{API}/admin/steps?survey_slug=aerzte", timeout=20).json()
        if item["step_type"] == "partner_selection"
    )
    email = f"orphan-partner-ui-{uuid4().hex[:8]}@test.de"
    created = session.post(
        f"{API}/admin/users",
        json={
            "email": email,
            "password": "Test123!",
            "name": "Orphan Partner UI",
            "role": "user",
            "survey_id": survey["id"],
        },
        timeout=20,
    )
    created.raise_for_status()
    user_id = created.json()["id"]
    session.put(
        f"{API}/admin/users/{user_id}/progress",
        json={
            "step_id": partner_step["id"],
            "status": "completed",
            "data": {"selected_partner_name": "Missing Browser Partner"},
        },
        timeout=20,
    ).raise_for_status()
    expected_names = [
        partner["name"] for partner in session.get(f"{API}/admin/partners", timeout=20).json()
    ]

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--host-resolver-rules=MAP localhost host.docker.internal"],
            )
            context = browser.new_context(viewport={"width": 1600, "height": 1000})
            install_api_proxy(context, BACKEND)
            page = context.new_page()
            page.goto(f"{FRONTEND}/login", wait_until="networkidle")
            page.locator('[data-testid="login-email-input"]').fill("admin@example.com")
            page.locator('[data-testid="login-password-input"]').fill("Admin123!")
            page.locator('[data-testid="login-submit-btn"]').click()
            page.wait_for_url("**/admin**", timeout=20000)

            page.locator('[data-testid="admin-users-tab"]').click()
            expect(page.locator('[data-testid="user-search-input"]')).to_be_visible(timeout=20000)
            page.locator('[data-testid="user-search-input"]').fill(email)
            warning = page.locator(f'[data-testid="user-orphaned-partners-{user_id}"]')
            expect(warning).to_be_visible(timeout=20000)
            expect(page.locator(f'[data-testid="user-partners-{user_id}"]')).not_to_contain_text(
                "Missing Browser Partner"
            )

            page.locator('[data-testid="create-user-btn"]').click()
            page.locator('[data-testid="create-user-role"]').click()
            page.get_by_role("option", name="Partner", exact=True).click()
            page.locator('[data-testid="create-user-partner"]').click()
            option_texts = page.locator('[role="option"]').all_inner_texts()
            actual_names = [name for name in option_texts if name in set(expected_names)]
            assert actual_names == sorted(expected_names, key=str.casefold)
            assert actual_names == expected_names
            context.close()
            browser.close()
    finally:
        session.delete(f"{API}/admin/users/{user_id}", timeout=20)
