"""E2E smoke tests for CMS-driven landing pages.

Requires the local frontend dev server and backend API to be running.
"""
import os
from uuid import uuid4
import requests

from dotenv import load_dotenv
from playwright.sync_api import expect, sync_playwright

from e2e_screenshots import capture_page, install_api_proxy


load_dotenv("/app/frontend/.env")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def _page_text(path: str, screenshot_name: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--host-resolver-rules=MAP localhost host.docker.internal",
            ],
        )
        page = browser.new_page()
        install_api_proxy(page.context, "http://localhost:8001")
        page.goto(f"{FRONTEND_URL}{path}", wait_until="networkidle", timeout=30000)
        text = page.locator("body").inner_text(timeout=10000)
        cta = page.locator("a:has([data-testid='hero-cta-btn'])").first
        register_href = cta.get_attribute("href") if cta.count() else None
        capture_page(page, "landing-pages", screenshot_name)
        browser.close()
        return text, register_href


def test_aerzte_landing_uses_aerzte_path():
    text, register_href = _page_text("/aerzte", "01-aerzte-landingpage")
    assert "PRAKTIZIEREN IN DEUTSCHLAND" in text
    assert any(
        title in text
        for title in (
            "IHCA - dein persönlicher Weg zum Facharzt in Deutschland",
            "IHCA - dein persoenlicher Weg zum Facharzt in Deutschland",
        )
    )
    assert register_href == "/s/aerzte/register"


def test_root_is_partner_registration_landing():
    text, _ = _page_text("/", "00-partner-registration")
    assert "Als Partner registrieren" in text
    assert "Stripe" in text


def test_partner_registration_redirects_to_isolated_payment_route():
    email = f"partner-payment-e2e-{uuid4().hex[:10]}@example.com"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--host-resolver-rules=MAP localhost host.docker.internal"])
        page = browser.new_page()
        install_api_proxy(page.context, "http://localhost:8001")
        page.goto(f"{FRONTEND_URL}/", wait_until="networkidle", timeout=30000)
        page.get_by_label("Unternehmen *").fill("Browser Partner GmbH")
        page.get_by_label("Ansprechpartner *").fill("Browser Test")
        page.get_by_label("E-Mail *").fill(email)
        page.get_by_label("Passwort *").fill("Partner123!")
        page.get_by_role("button", name="Partnerkonto erstellen").click()
        page.wait_for_url("**/partner-payment", timeout=20000)
        expect(page.get_by_role("heading", name="Partnerzugang freischalten")).to_be_visible(timeout=10000)
        assert "Partnerzugang freischalten" in page.locator("body").inner_text()
        assert "Account Not Linked" not in page.locator("body").inner_text()
        browser.close()

    admin = requests.post("http://localhost:8001/api/auth/login", json={"email": "admin@example.com", "password": "Admin123!"}, timeout=20).json()
    partners = requests.get("http://localhost:8001/api/admin/partners", headers={"Authorization": f"Bearer {admin['access_token']}"}, timeout=20).json()
    partner = next(p for p in partners if p.get("contact_email") == email)
    requests.delete(f"http://localhost:8001/api/admin/partners/{partner['id']}", headers={"Authorization": f"Bearer {admin['access_token']}"}, timeout=20)


def test_pflege_landing_uses_pflege_path_and_survey_registration():
    text, register_href = _page_text("/pflege", "02-pflege-landingpage")
    assert "PFLEGE IN DEUTSCHLAND" in text
    assert "Anerkennung als Pflegefachkraft in Deutschland" in text
    assert "Ihr Weg in die Pflege in Deutschland" in text
    assert register_href == "/s/pflege/register"
