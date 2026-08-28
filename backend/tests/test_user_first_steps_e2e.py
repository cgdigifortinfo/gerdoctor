"""Browser regression for sequential progress after user registration.

Completing the first survey form must not interpret ``anerkennungsstatus`` as
permission to finish later workflow blocks.  The browser must advance exactly
one step and the next four persisted progress records must remain unfinished.
"""
from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import requests
from playwright.sync_api import expect, sync_playwright

from e2e_screenshots import install_api_proxy


BACKEND = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
FRONTEND = os.environ.get("FRONTEND_URL", "http://localhost:3001").rstrip("/")
API = f"{BACKEND}/api"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin123!"
USER_PASSWORD = "Sequential123!"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _admin_token() -> str:
    response = requests.post(
        f"{API}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _fill_first_form(page, step: dict) -> None:
    for field in step.get("fields") or []:
        if not field.get("required") or field.get("field_type") in {
            "heading", "paragraph", "html", "image", "divider",
        }:
            continue
        name = field["name"]
        field_type = field.get("field_type", "text")
        locator = page.locator(f'[data-testid="form-field-{name}"]:visible').first

        if field_type in {"select", "selectbox"}:
            locator.click()
            options = page.get_by_role("option")
            if name == "anerkennungsstatus":
                desired = options.filter(has_text="Ich bin in Deutschland approbiert")
                (desired if desired.count() else options.first).click()
            else:
                options.first.click()
        elif field_type in {"radio", "decision"}:
            locator.locator('input[type="radio"]').first.check()
        elif field_type == "checkbox":
            locator.check()
        elif field_type == "multiselect":
            locator.locator('input[type="checkbox"]').first.check()
        else:
            value = "1990-01-01" if field_type == "date" else f"E2E {name}"
            if field_type == "email":
                value = "sequential@example.com"
            elif field_type == "number":
                value = "1"
            locator.fill(value)


def test_new_user_completes_only_the_current_step_and_advances_to_step_two():
    admin_token = _admin_token()
    email = f"e2e-sequential-{uuid4().hex[:10]}@example.com"
    user_id = ""

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--host-resolver-rules=MAP localhost host.docker.internal"],
            )
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            install_api_proxy(context, BACKEND)
            page = context.new_page()
            page.goto(f"{FRONTEND}/s/aerzte/register", wait_until="domcontentloaded")

            page.locator('[data-testid="register-name-input"]').fill("E2E Sequential User")
            page.locator('[data-testid="register-email-input"]').fill(email)
            page.locator('[data-testid="register-password-input"]').fill(USER_PASSWORD)
            page.locator('[data-testid="register-confirm-password-input"]').fill(USER_PASSWORD)
            with page.expect_response(
                lambda response: response.request.method == "POST" and "/api/auth/register" in response.url,
            ) as registration_info:
                page.locator('[data-testid="register-submit-btn"]').click()

            registration = registration_info.value.json()
            token = registration["access_token"]
            user_id = registration["id"]
            expect(page.locator('[data-testid="journey-step-counter"]:visible').first).to_contain_text(
                "Schritt 1", timeout=30000,
            )

            bootstrap = requests.get(
                f"{API}/steps/bootstrap", headers=_headers(token), timeout=20,
            ).json()
            first_five = sorted(bootstrap["steps"], key=lambda item: item["order"])[:5]
            assert len(first_five) == 5

            _fill_first_form(page, first_five[0])
            with page.expect_response(
                lambda response: response.request.method == "PUT" and "/api/steps/progress" in response.url,
            ) as progress_info:
                page.locator('[data-testid="complete-step-btn"]:visible').first.click()
            assert progress_info.value.status == 200

            expect(page.locator('[data-testid="journey-step-counter"]:visible').first).to_contain_text(
                "Schritt 2", timeout=30000,
            )
            progress = requests.get(
                f"{API}/steps/progress", headers=_headers(token), timeout=20,
            ).json()
            progress_by_step = {row["step_id"]: row for row in progress}

            assert progress_by_step[first_five[0]["id"]]["status"] == "completed"
            assert all(
                progress_by_step[step["id"]]["status"] != "completed"
                for step in first_five[1:]
            )
            assert not any(
                (progress_by_step[step["id"]].get("data") or {}).get("auto_skipped_by_status")
                for step in first_five[1:]
            )

            # Continue through fast-lane choice and the first workflow choice,
            # then upload a real PDF through the browser.
            page.locator('[data-testid="decision-option-1"]:visible').click()
            expect(page.locator('[data-testid="journey-current-title"]:visible').first).to_contain_text(
                first_five[2]["title"], timeout=30000,
            )
            page.locator('[data-testid="decision-option-0"]:visible').click()
            expect(page.locator('[data-testid="journey-current-title"]:visible').first).to_contain_text(
                first_five[3]["title"], timeout=30000,
            )

            page.locator('[data-testid="add-multiupload-documents"]:visible').click()
            entry = page.locator('[data-testid="multiupload-entry-0"]:visible')
            entry.locator('button[role="combobox"]').click()
            page.get_by_role("option").first.click()
            pdf = Path("/app/output/pdf/demo-sprachnachweis.pdf")
            assert pdf.is_file()
            with page.expect_response(
                lambda response: response.request.method == "POST" and "/api/files/upload" in response.url,
            ) as upload_info:
                entry.locator('input[type="file"]').set_input_files(str(pdf))
            assert upload_info.value.status == 200
            with page.expect_response(
                lambda response: response.request.method == "PUT" and "/api/steps/progress" in response.url,
            ) as upload_progress_info:
                page.locator('[data-testid="complete-step-btn"]:visible').first.click()
            assert upload_progress_info.value.status == 200

            steps_by_order = {step["order"]: step for step in bootstrap["steps"]}
            milestone = steps_by_order[6]
            next_selection = steps_by_order[7]
            expect(page.locator('[data-testid="journey-current-title"]:visible').first).to_contain_text(
                next_selection["title"], timeout=30000,
            )

            # Return through the completed milestone to the now read-only
            # upload overview. Both completed pages must offer a forward path.
            page.locator('[data-testid="prev-step-btn"]:visible').click()
            expect(page.locator('[data-testid="journey-current-title"]:visible').first).to_contain_text(
                milestone["title"], timeout=30000,
            )
            expect(page.locator('[data-testid="workflow-document-0"]:visible')).to_contain_text(
                pdf.name,
            )
            page.locator('[data-testid="prev-step-btn"]:visible').click()
            expect(page.locator('[data-testid="journey-current-title"]:visible').first).to_contain_text(
                first_five[3]["title"], timeout=30000,
            )
            expect(page.locator('[data-testid="step-read-only"]:visible')).to_contain_text(pdf.name)
            page.locator('[data-testid="step-next-btn"]:visible').click()
            expect(page.locator('[data-testid="journey-current-title"]:visible').first).to_contain_text(
                milestone["title"], timeout=30000,
            )
            page.locator('[data-testid="milestone-next-btn"]:visible').click()
            expect(page.locator('[data-testid="journey-current-title"]:visible').first).to_contain_text(
                next_selection["title"], timeout=30000,
            )
            browser.close()
    finally:
        if user_id:
            requests.delete(
                f"{API}/admin/users/{user_id}", headers=_headers(admin_token), timeout=20,
            ).raise_for_status()
