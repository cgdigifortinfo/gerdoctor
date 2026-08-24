"""Browser regression for decision -> partner selection -> waiting milestone.

The active step must be recalculated after a decision changes which steps are
visible.  In particular, the UI must never use the old visible-step index and
jump directly to the milestone while no partner has been selected.
"""

import os
from uuid import uuid4

import pytest
import requests
from playwright.sync_api import expect, sync_playwright

from e2e_screenshots import install_api_proxy


BACKEND = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
FRONTEND = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
API = f"{BACKEND}/api"
PASSWORD = "Branch123!"


def _headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def survey_context():
    login = requests.post(
        f"{API}/auth/login",
        json={"email": "admin@example.com", "password": "Admin123!"},
        timeout=20,
    )
    login.raise_for_status()
    token = login.json()["access_token"]
    headers = _headers(token)
    surveys = requests.get(f"{API}/admin/surveys", headers=headers, timeout=20).json()
    survey = next(item for item in surveys if item["slug"] == "aerzte")
    steps = requests.get(
        f"{API}/admin/steps?survey_slug=aerzte", headers=headers, timeout=20
    ).json()
    yield token, survey, sorted(steps, key=lambda item: item["order"])


def _decision_value(step, wanted):
    field = next(
        (field for field in step.get("fields", []) if field.get("field_type") == "decision"),
        step.get("fields", [{}])[0],
    )
    options = field.get("options", [])
    for index, option in enumerate(options):
        value = option.get("value") if isinstance(option, dict) else option
        if value == wanted:
            return index
    raise AssertionError(f"Decision {step['order']} has no option {wanted!r}: {options!r}")


def _browser_title(step):
    """Fresh browser contexts currently default to the English UI."""
    return step.get("translations", {}).get("en", {}).get("title") or step["title"]


def _create_user_at_decision(admin_token, survey, steps, decision_order):
    email = f"partner-branch-e2e-{decision_order}-{uuid4().hex[:8]}@test.de"
    created = requests.post(
        f"{API}/admin/users",
        headers=_headers(admin_token),
        json={
            "email": email,
            "password": PASSWORD,
            "name": f"Partner Branch E2E {decision_order}",
            "role": "user",
            "survey_id": survey["id"],
        },
        timeout=20,
    )
    created.raise_for_status()
    user_id = created.json()["id"]

    for step in steps:
        if step["order"] >= decision_order:
            break
        data = {}
        if step["step_type"] == "decision":
            data = {"decision": "selber" if step["order"] == 2 else "upload"}
        updated = requests.put(
            f"{API}/admin/users/{user_id}/progress",
            headers=_headers(admin_token),
            json={"step_id": step["id"], "status": "completed", "data": data},
            timeout=20,
        )
        updated.raise_for_status()
    return user_id, email


def _login_user(page, email):
    page.goto(f"{FRONTEND}/login", wait_until="networkidle")
    page.locator('[data-testid="login-email-input"]').fill(email)
    page.locator('[data-testid="login-password-input"]').fill(PASSWORD)
    page.locator('[data-testid="login-submit-btn"]').click()
    page.wait_for_url("**/dashboard**", timeout=20000)


def test_every_partner_branch_requires_selection_before_waiting(survey_context):
    admin_token, survey, steps = survey_context
    by_order = {step["order"]: step for step in steps}
    # The five single-partner blocks plus the Jobangebote multi-partner block.
    patterns = [
        (3, 5, 6, "partner", False),
        (7, 9, 10, "partner", False),
        (11, 13, 14, "partner", False),
        (15, 17, 18, "partner", False),
        (19, 20, 21, "partner_nutzen", True),
        (22, 24, 25, "partner", False),
    ]
    created_user_ids = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--host-resolver-rules=MAP localhost host.docker.internal"],
            )
            for decision_order, partner_order, milestone_order, value, multi in patterns:
                user_id, email = _create_user_at_decision(
                    admin_token, survey, steps, decision_order
                )
                created_user_ids.append(user_id)
                context = browser.new_context(viewport={"width": 1440, "height": 1000})
                install_api_proxy(context, BACKEND)
                page = context.new_page()
                _login_user(page, email)

                decision = by_order[decision_order]
                partner = by_order[partner_order]
                milestone = by_order[milestone_order]
                expect(page.locator("h1")).to_have_text(_browser_title(decision), timeout=30000)
                expect(page.locator('[data-testid="decision-step"]').last).to_be_visible()

                option_index = _decision_value(decision, value)
                page.locator(f'[data-testid="decision-option-{option_index}"]').click()

                # Core regression: the branch selection is active, never the
                # waiting milestone, while no partner has been selected.
                expect(page.locator("h1")).to_have_text(_browser_title(partner), timeout=30000)
                expect(page.locator("h1")).not_to_have_text(_browser_title(milestone))
                confirm_testid = "confirm-multipartner-btn" if multi else "confirm-partner-btn"
                confirm = page.locator(f'[data-testid="{confirm_testid}"]').last
                expect(confirm).to_be_disabled()

                # Back navigation must return to the decision. Rechoosing the
                # partner path must deterministically return to selection.
                page.locator('[data-testid="prev-step-btn"]').last.click()
                expect(page.locator("h1")).to_have_text(_browser_title(decision))
                page.locator(f'[data-testid="decision-option-{option_index}"]').click()
                expect(page.locator("h1")).to_have_text(_browser_title(partner), timeout=30000)

                card = page.locator(
                    '[data-testid^="partner-multiselect-"]'
                    if multi
                    else '[data-testid^="partner-select-"]'
                ).last
                expect(card).to_be_visible(timeout=30000)
                card.click()
                expect(confirm).to_be_enabled()
                confirm.click()

                # Waiting is correct only after a real partner submission.
                expect(page.locator("h1")).to_have_text(_browser_title(milestone), timeout=30000)
                expect(
                    page.get_by_text("Dieser Schritt wird von Ihrem Partner bearbeitet.").last
                ).to_be_visible()
                context.close()
            browser.close()
    finally:
        for user_id in created_user_ids:
            requests.delete(
                f"{API}/admin/users/{user_id}",
                headers=_headers(admin_token),
                timeout=20,
            )
