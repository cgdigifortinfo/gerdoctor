"""Regression test: the browser must not load former app-builder telemetry."""

import os
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3001").rstrip("/")
FORBIDDEN_HOST_PARTS = ("posthog.com", "emergent.sh", "emergentagent.com")


def test_public_routes_do_not_load_builder_tracking():
    requested_urls = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--host-resolver-rules=MAP localhost host.docker.internal",
            ],
        )
        page = browser.new_page()
        page.on("request", lambda request: requested_urls.append(request.url))

        for path in ("/", "/login", "/register"):
            response = page.goto(f"{FRONTEND_URL}{path}", wait_until="networkidle")
            assert response and response.ok, f"Frontend route failed: {path}"
            assert page.locator("#emergent-badge").count() == 0
            assert page.evaluate("typeof window.posthog") == "undefined"

        browser.close()

    forbidden = [
        url
        for url in requested_urls
        if any(part in (urlparse(url).hostname or "").lower() for part in FORBIDDEN_HOST_PARTS)
    ]
    assert forbidden == [], f"Former builder hosts were requested: {forbidden}"
