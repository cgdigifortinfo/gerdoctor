"""Admin survey/steps E2E regressions.

Covers:
- The "URL öffnen" button links to the admin steps deep-link for the selected
  survey's first step instead of the public landing that redirects admins.
- Switching the survey in the steps tab closes a stale step editor and reloads
  the list for the newly selected survey.
"""
import os
import time
import uuid

import pytest
import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, expect


load_dotenv("/app/frontend/.env")

BACKEND = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
FRONTEND = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
API = f"{BACKEND}/api"

ADMIN_EMAIL = "admin@example.com"
ADMIN_PW = "Admin123!"


def _admin_token():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PW},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_state():
    token = _admin_token()
    surveys = requests.get(f"{API}/admin/surveys", headers=_auth(token), timeout=15).json()
    by_slug = {s["slug"]: s for s in surveys}
    assert "aerzte" in by_slug
    assert "pflege" in by_slug

    created_step_ids = []
    title = f"PFLEGE E2E First Step {int(time.time())}-{uuid.uuid4().hex[:4]}"
    second_title = f"PFLEGE E2E Flow Step {int(time.time())}-{uuid.uuid4().hex[:4]}"
    for order, step_title in ((901, title), (902, second_title)):
        create = requests.post(
            f"{API}/admin/steps",
            headers=_auth(token),
            json={
                "survey_id": by_slug["pflege"]["id"],
                "title": step_title,
                "description": "Temporary Pflege step for admin survey switching E2E.",
                "order": order,
                "step_type": "display",
                "fields": [],
            },
            timeout=15,
        )
        create.raise_for_status()
        created_step_ids.append(create.json()["id"])
    yield {"pflege_title": title, "pflege_second_title": second_title}
    for step_id in created_step_ids:
        requests.delete(f"{API}/admin/steps/{step_id}", headers=_auth(token), timeout=15)


def _login_admin(page):
    page.goto(f"{FRONTEND}/login", wait_until="networkidle")
    page.locator('[data-testid="login-email-input"]').fill(ADMIN_EMAIL)
    page.locator('[data-testid="login-password-input"]').fill(ADMIN_PW)
    page.locator('[data-testid="login-submit-btn"]').click()
    page.wait_for_url("**/admin**", timeout=15000)


def _choose_select_option(page, trigger_testid, option_text):
    page.locator(f'[data-testid="{trigger_testid}"]').click()
    page.locator('[role="option"]').filter(has_text=option_text).last.click()


def _goto_admin_steps(page, survey_slug):
    page.goto(f"{FRONTEND}/admin?tab=steps&survey={survey_slug}&step=1", wait_until="domcontentloaded")
    try:
        expect(page.locator('[data-testid="admin-survey-select"]')).to_be_visible(timeout=30000)
    except AssertionError:
        page.reload(wait_until="domcontentloaded")
        expect(page.locator('[data-testid="admin-survey-select"]')).to_be_visible(timeout=30000)


def test_admin_steps_deep_link_and_survey_switch(admin_state):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--host-resolver-rules=MAP localhost host.docker.internal",
            ],
        )
        page = browser.new_page()
        _login_admin(page)

        _goto_admin_steps(page, "aerzte")
        expect(page.locator('[data-testid="step-row-order-1"]').first).to_contain_text("Persönliche Daten", timeout=30000)

        open_button_link = page.locator('a:has([data-testid="open-survey-url-btn"])').first
        expect(open_button_link).to_have_attribute("href", "/admin?tab=steps&survey=aerzte&step=1")

        page.locator('[data-testid^="edit-step-"]').first.click()
        expect(page.get_by_role("dialog")).to_be_visible()
        page.keyboard.press("Escape")
        expect(page.get_by_role("dialog")).to_have_count(0)

        _choose_select_option(page, "admin-survey-select", "FSP Pflege /s/pflege")
        expect(page.locator('[data-testid="admin-survey-select"]')).to_contain_text("FSP Pflege", timeout=10000)
        expect(page.locator('[data-testid="open-survey-url-btn"]')).to_be_visible()
        expect(page.locator('a:has([data-testid="open-survey-url-btn"])').first).to_have_attribute(
            "href",
            "/admin?tab=steps&survey=pflege&step=1",
        )
        expect(page.get_by_text(admin_state["pflege_title"])).to_be_visible(timeout=15000)
        expect(page.get_by_text("Persönliche Daten")).to_have_count(0)

        browser.close()


def test_admin_steps_url_survey_param_overrides_current_survey(admin_state):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--host-resolver-rules=MAP localhost host.docker.internal",
            ],
        )
        page = browser.new_page()
        _login_admin(page)

        _goto_admin_steps(page, "aerzte")
        expect(page.locator('[data-testid="admin-survey-select"]')).to_contain_text("Ärzte Anerkennung", timeout=30000)
        expect(page.locator('[data-testid="step-row-order-1"]').first).to_contain_text("Persönliche Daten", timeout=30000)

        _goto_admin_steps(page, "pflege")

        expect(page.locator('[data-testid="admin-survey-select"]')).to_contain_text("FSP Pflege", timeout=30000)
        expect(page.locator('a:has([data-testid="open-survey-url-btn"])').first).to_have_attribute(
            "href",
            "/admin?tab=steps&survey=pflege&step=1",
        )
        expect(page.get_by_text(admin_state["pflege_title"])).to_be_visible(timeout=15000)
        expect(page.get_by_text("Persönliche Daten")).to_have_count(0)

        browser.close()


def test_step_editor_survey_switch_keeps_editor_open_and_reloads(admin_state):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--host-resolver-rules=MAP localhost host.docker.internal",
            ],
        )
        page = browser.new_page()
        _login_admin(page)

        _goto_admin_steps(page, "aerzte")
        expect(page.locator('[data-testid="step-row-order-1"]').first).to_contain_text("Persönliche Daten", timeout=30000)

        page.locator('[data-testid^="edit-step-"]').first.click()
        expect(page.get_by_role("dialog")).to_be_visible()
        expect(page.locator('[data-testid="step-survey-select"]')).to_contain_text("Ärzte Anerkennung")

        _choose_select_option(page, "step-survey-select", "FSP Pflege /s/pflege")

        expect(page.get_by_role("dialog")).to_be_visible(timeout=10000)
        expect(page.locator('[data-testid="step-survey-select"]')).to_contain_text("FSP Pflege", timeout=10000)
        expect(page.locator('[data-testid="admin-survey-select"]')).to_contain_text("FSP Pflege", timeout=10000)
        expect(page.locator('a:has([data-testid="open-survey-url-btn"])').first).to_have_attribute(
            "href",
            "/admin?tab=steps&survey=pflege&step=1",
        )
        expect(page.locator('[data-testid="step-title-input"]')).to_have_value("", timeout=10000)

        page.keyboard.press("Escape")
        expect(page.get_by_role("dialog")).to_have_count(0)
        expect(page.get_by_text(admin_state["pflege_title"])).to_be_visible(timeout=15000)
        expect(page.get_by_text("Persönliche Daten")).to_have_count(0)

        browser.close()


def test_admin_survey_switch_loads_list_and_flow_views(admin_state):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--host-resolver-rules=MAP localhost host.docker.internal",
            ],
        )
        page = browser.new_page()
        _login_admin(page)

        _goto_admin_steps(page, "aerzte")
        expect(page.locator('[data-testid="admin-survey-select"]')).to_contain_text("Ärzte Anerkennung", timeout=30000)
        expect(page.locator('[data-testid="step-row-order-1"]').first).to_contain_text("Persönliche Daten", timeout=30000)

        page.locator('[data-testid="steps-view-flow"]').click()
        expect(page.locator('[data-testid="steps-flow-builder"]')).to_be_visible(timeout=15000)
        expect(page.locator('[data-testid^="flow-node-"]').filter(has_text="Persönliche Daten").first).to_be_visible(timeout=15000)

        _choose_select_option(page, "admin-survey-select", "FSP Pflege /s/pflege")
        expect(page.locator('[data-testid="admin-survey-select"]')).to_contain_text("FSP Pflege", timeout=15000)
        expect(page.get_by_text(admin_state["pflege_title"])).to_be_visible(timeout=15000)
        expect(page.locator('[data-testid="steps-list-empty-state"]')).to_have_count(0)
        expect(page.get_by_text("Persönliche Daten")).to_have_count(0)

        page.locator('[data-testid="steps-view-flow"]').click()
        expect(page.locator('[data-testid="steps-flow-builder"]')).to_be_visible(timeout=15000)
        expect(page.locator('[data-testid="flow-empty-state"]')).to_have_count(0)
        expect(page.locator('[data-testid^="flow-node-"]').filter(has_text=admin_state["pflege_title"]).first).to_be_visible(timeout=15000)
        expect(page.locator('[data-testid^="flow-node-"]').filter(has_text=admin_state["pflege_second_title"]).first).to_be_visible(timeout=15000)

        page.locator('[data-testid="steps-view-list"]').click()
        expect(page.get_by_text(admin_state["pflege_title"])).to_be_visible(timeout=15000)
        expect(page.get_by_text(admin_state["pflege_second_title"])).to_be_visible(timeout=15000)

        browser.close()
