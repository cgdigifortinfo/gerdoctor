"""E2E coverage for configurable admin and partner pagination."""

import os

from dotenv import load_dotenv
from playwright.sync_api import expect, sync_playwright

from e2e_screenshots import capture_page, install_api_proxy


load_dotenv("/app/frontend/.env")

BACKEND = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
FRONTEND = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def _browser(playwright):
    return playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--host-resolver-rules=MAP localhost host.docker.internal",
        ],
    )


def _page(browser):
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    install_api_proxy(context, BACKEND)
    return context, context.new_page()


def _login(page, email, password, destination):
    page.goto(f"{FRONTEND}/login", wait_until="networkidle")
    page.locator('[data-testid="login-email-input"]').fill(email)
    page.locator('[data-testid="login-password-input"]').fill(password)
    page.locator('[data-testid="login-submit-btn"]').click()
    page.wait_for_url(f"**{destination}**", timeout=15000)
    page.wait_for_load_state("networkidle")


def _select_page_size(page, pagination_id, label):
    page.locator(f'[data-testid="page-size-{pagination_id}"]').click()
    page.get_by_role("option", name=label, exact=True).click()


def test_admin_lists_have_configurable_pagination_and_show_all():
    with sync_playwright() as playwright:
        browser = _browser(playwright)
        context, page = _page(browser)
        _login(page, "admin@example.com", "Admin123!", "/admin")

        page.locator('[data-testid="admin-steps-tab"]').click()
        page.locator('[data-testid="steps-view-list"]').click()
        expect(page.locator('[data-testid="pagination-admin-steps"]')).to_be_visible(timeout=15000)
        expect(page.locator('[data-testid^="step-row-order-"]')).to_have_count(10)

        page.locator('[data-testid="pagination-next-admin-steps"]').click()
        expect(page.locator('[data-testid="pagination-page-admin-steps"]')).to_contain_text("Seite 2")

        _select_page_size(page, "admin-steps", "Alle")
        expect(page.locator('[data-testid^="step-row-order-"]')).to_have_count(25)
        expect(page.locator('[data-testid="pagination-summary-admin-steps"]')).to_contain_text("1–25 von 25")

        page.locator('[data-testid="admin-users-tab"]').click()
        expect(page.locator('[data-testid="pagination-admin-users"]')).to_be_visible()
        _select_page_size(page, "admin-users", "Alle")
        expect(page.locator('[data-testid="pagination-page-admin-users"]')).to_have_count(0)

        page.locator('[data-testid="admin-partners-tab"]').click()
        expect(page.locator('[data-testid="pagination-admin-partners"]')).to_be_visible()

        page.locator('[data-testid="admin-audit-tab"]').click()
        expect(page.locator('[data-testid="pagination-admin-audit"]')).to_be_visible()

        capture_page(page, "pagination", "01-admin-audit-pagination")
        context.close()
        browser.close()


def test_partner_user_lists_have_independent_pagination():
    with sync_playwright() as playwright:
        browser = _browser(playwright)
        context, page = _page(browser)
        _login(page, "partner-example@chrizz1001.de", "Partner123!", "/partner-dashboard")

        expect(page.locator('[data-testid="pagination-partner-my-users"]')).to_be_visible(timeout=15000)
        _select_page_size(page, "partner-my-users", "Alle")

        page.locator('[data-testid="tab-completed-users"]').click()
        expect(page.locator('[data-testid="pagination-partner-completed-users"]')).to_be_visible()

        page.locator('[data-testid="tab-other-users"]').click()
        expect(page.locator('[data-testid="pagination-partner-other-users"]')).to_be_visible()
        _select_page_size(page, "partner-other-users", "25")

        capture_page(page, "pagination", "02-partner-user-pagination")
        context.close()
        browser.close()
