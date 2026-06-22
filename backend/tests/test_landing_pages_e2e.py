"""E2E smoke tests for CMS-driven landing pages.

Requires the local frontend dev server and backend API to be running.
"""
import os

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright


load_dotenv("/app/frontend/.env")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def _page_text(path: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--host-resolver-rules=MAP localhost host.docker.internal",
            ],
        )
        page = browser.new_page()
        page.goto(f"{FRONTEND_URL}{path}", wait_until="networkidle", timeout=30000)
        text = page.locator("body").inner_text(timeout=10000)
        register_href = page.locator("a:has([data-testid='hero-cta-btn'])").first.get_attribute("href")
        browser.close()
        return text, register_href


def test_default_landing_stays_on_root():
    text, register_href = _page_text("/")
    assert "PRAKTIZIEREN IN DEUTSCHLAND" in text
    assert "IHCA - dein persoenlicher Weg zum Facharzt in Deutschland" in text
    assert register_href == "/s/aerzte/register"


def test_pflege_landing_uses_pflege_path_and_survey_registration():
    text, register_href = _page_text("/pflege")
    assert "PFLEGE IN DEUTSCHLAND" in text
    assert "Anerkennung als Pflegefachkraft in Deutschland" in text
    assert "Ihr Weg in die Pflege in Deutschland" in text
    assert register_href == "/s/pflege/register"
