"""Visual smoke walkthrough for every routed frontend view.

Run from the backend container:
  python tests/e2e_design_views.py
"""

import os
import sys

from dotenv import load_dotenv
from playwright.sync_api import expect, sync_playwright

from e2e_screenshots import capture_page, install_api_proxy


load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BACKEND = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
FRONTEND = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
SUITE = "design-views"


def new_page(browser):
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    install_api_proxy(context, BACKEND)
    return context, context.new_page()


def login(page, email, password, destination):
    page.goto(f"{FRONTEND}/login", wait_until="networkidle")
    page.locator('[data-testid="login-email-input"]').fill(email)
    page.locator('[data-testid="login-password-input"]').fill(password)
    page.locator('[data-testid="login-submit-btn"]').click()
    page.wait_for_url(f"**{destination}**", timeout=15000)
    page.wait_for_load_state("networkidle")


def run():
    captures = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--host-resolver-rules=MAP localhost host.docker.internal",
            ],
        )

        context, page = new_page(browser)
        for path, name, selector in (
            ("/login", "01-login", '[data-testid="login-email-input"]'),
            ("/register", "02-register", '[data-testid="register-name-input"]'),
            ("/forgot-password", "03-forgot-password", '[data-testid="forgot-email-input"]'),
            ("/reset-password", "04-invalid-reset-link", "h1"),
        ):
            page.goto(f"{FRONTEND}{path}", wait_until="networkidle")
            expect(page.locator(selector).first).to_be_visible(timeout=10000)
            captures.append(capture_page(page, SUITE, name))
        context.close()

        context, page = new_page(browser)
        login(page, "dr.schmidt@chrizz1001.de", "Demo123!", "/dashboard")
        expect(page.locator('[data-testid="logout-btn"]')).to_be_visible(timeout=10000)
        captures.append(capture_page(page, SUITE, "05-user-dashboard"))
        context.close()

        context, page = new_page(browser)
        login(page, "partner-example@chrizz1001.de", "Partner123!", "/partner-dashboard")
        expect(page.locator('[data-testid="partner-logout-btn"]')).to_be_visible(timeout=10000)
        captures.append(capture_page(page, SUITE, "06-partner-dashboard"))
        context.close()

        context, page = new_page(browser)
        login(page, "admin@example.com", "Admin123!", "/admin")
        expect(page.locator('[data-testid="admin-logout-btn"]')).to_be_visible(timeout=10000)
        captures.append(capture_page(page, SUITE, "07-admin-dashboard"))
        context.close()

        browser.close()

    print(f"Visual design views: {len(captures)}/7 captured")
    return 0 if len(captures) == 7 else 1


if __name__ == "__main__":
    sys.exit(run())
