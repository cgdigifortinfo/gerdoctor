"""Shared screenshot output for the browser end-to-end tests."""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlsplit


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCREENSHOT_DIR = PROJECT_ROOT / "test_results" / "e2e-screenshots"


def _slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    return value.strip("-._") or "page"


def screenshot_dir() -> Path:
    """Return and create the configurable root directory for E2E screenshots."""
    result_dir = Path(
        os.environ.get("E2E_SCREENSHOT_DIR", str(DEFAULT_SCREENSHOT_DIR))
    ).expanduser()
    result_dir.mkdir(parents=True, exist_ok=True)
    return result_dir


def screenshot_path(suite: str, name: str) -> Path:
    """Build a stable PNG path grouped by test suite."""
    suite_dir = screenshot_dir() / _slug(suite)
    suite_dir.mkdir(parents=True, exist_ok=True)
    return suite_dir / f"{_slug(name)}.png"


def capture_page(page, suite: str, name: str) -> Path:
    """Capture a full-page screenshot with sync Playwright."""
    path = screenshot_path(suite, name)
    page.screenshot(path=str(path), full_page=True, animations="disabled")
    return path


async def capture_page_async(page, suite: str, name: str) -> Path:
    """Capture a full-page screenshot with async Playwright."""
    path = screenshot_path(suite, name)
    await page.screenshot(path=str(path), full_page=True, animations="disabled")
    return path


def _proxied_api_url(backend_url: str, request_url: str) -> str:
    parsed = urlsplit(request_url)
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{backend_url.rstrip('/')}{parsed.path}{query}"


def install_api_proxy(browser_target, backend_url: str) -> None:
    """Proxy browser `/api` requests through Playwright's sync request client."""

    def forward(route):
        response = route.fetch(url=_proxied_api_url(backend_url, route.request.url))
        route.fulfill(response=response)

    browser_target.route("**/api/**", forward)


async def install_api_proxy_async(browser_target, backend_url: str) -> None:
    """Proxy browser `/api` requests through Playwright's async request client."""

    async def forward(route):
        response = await route.fetch(
            url=_proxied_api_url(backend_url, route.request.url)
        )
        await route.fulfill(response=response)

    await browser_target.route("**/api/**", forward)
