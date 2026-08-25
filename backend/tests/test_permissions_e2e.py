"""Browser E2E for permission-group CRUD and user-specific overrides."""
import os
import uuid

import requests
from playwright.sync_api import expect, sync_playwright

from e2e_screenshots import capture_page


BACKEND = (os.environ.get("E2E_BACKEND_URL") or "http://localhost:8001").rstrip("/")
FRONTEND = os.environ.get("FRONTEND_URL", "http://localhost:3001").rstrip("/")
API = f"{BACKEND}/api"


def _admin():
    response = requests.post(f"{API}/auth/login", json={"email": "admin@example.com", "password": "Admin123!"}, timeout=15)
    response.raise_for_status()
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _login_admin(page):
    page.goto(f"{FRONTEND}/login", wait_until="networkidle")
    page.locator('[data-testid="login-email-input"]').fill("admin@example.com")
    page.locator('[data-testid="login-password-input"]').fill("Admin123!")
    page.locator('[data-testid="login-submit-btn"]').click()
    page.wait_for_url("**/admin**", timeout=15000)


def _select_searchable(page, test_id, search, option_text):
    page.locator(f'[data-testid="{test_id}"]').click()
    search_input = page.locator(f'[data-testid="{test_id}-search"]')
    expect(search_input).to_be_visible(timeout=5000)
    search_input.fill(search)
    option = page.locator(f'[data-testid="{test_id}-option"]').filter(
        has=page.get_by_text(option_text, exact=True)
    )
    expect(option).to_be_visible(timeout=5000)
    option.click()
    page.locator(f'[data-testid="{test_id}-done"]').click()


def test_permission_groups_crud_and_user_overrides_in_admin_ui():
    headers = _admin()
    suffix = uuid.uuid4().hex[:8]
    group_name = f"E2E Rechteverwaltung {suffix}"
    user_email = f"rbac-ui-{suffix}@test.de"
    group_id = user_id = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--host-resolver-rules=MAP localhost host.docker.internal"])
            page = browser.new_page(viewport={"width": 1700, "height": 1050})
            _login_admin(page)
            page.goto(f"{FRONTEND}/admin?tab=users", wait_until="domcontentloaded")
            expect(page.locator('[data-testid="user-management-sections"]')).to_be_visible(timeout=30000)
            page.locator('[data-testid="show-permission-groups"]').click()
            manager = page.locator('[data-testid="permission-groups-manager"]')
            expect(manager).to_be_visible()
            expect(manager.get_by_role("heading", name="Administratoren")).to_be_visible()
            expect(manager.get_by_role("heading", name="Survey-Nutzer")).to_be_visible()
            expect(manager.get_by_role("heading", name="Partner", exact=True)).to_be_visible()
            capture_page(page, "permissions", "01-standardgruppen")

            page.locator('[data-testid="create-permission-group"]').click()
            page.locator('[data-testid="permission-group-name"]').fill(group_name)
            page.locator('[data-testid="permission-group-role"]').click()
            page.locator('[role="option"]').filter(has_text="Administration").click()
            for permission in ("admin.access", "users.view", "groups.view"):
                page.locator(f'[data-testid="group-permission-matrix-{permission}"]').click()
            capture_page(page, "permissions", "02-gruppe-mit-einzelrechten")
            page.locator('[data-testid="save-permission-group"]').click()
            expect(page.get_by_text("Nutzergruppe erstellt")).to_be_visible(timeout=10000)
            expect(page.get_by_text(group_name, exact=True)).to_be_visible()

            groups = requests.get(f"{API}/admin/permission-groups", headers=headers, timeout=15).json()
            created_group = next(group for group in groups if group["name"] == group_name)
            group_id = created_group["id"]
            page.get_by_role("button", name=f"{group_name} bearbeiten").click()
            page.locator('[data-testid="group-permission-matrix-users.export"]').click()
            page.locator('[data-testid="save-permission-group"]').click()
            expect(page.get_by_text("Nutzergruppe aktualisiert")).to_be_visible(timeout=10000)
            updated = requests.get(f"{API}/admin/permission-groups", headers=headers, timeout=15).json()
            assert "users.export" in next(group for group in updated if group["id"] == group_id)["permissions"]
            capture_page(page, "permissions", "03-gruppe-aktualisiert")

            created_user = requests.post(
                f"{API}/admin/users",
                headers=headers,
                json={"email": user_email, "password": "Test123!", "name": "RBAC UI Test", "role": "admin", "group_ids": [group_id]},
                timeout=15,
            )
            created_user.raise_for_status()
            user_id = created_user.json()["id"]

            page.goto(f"{FRONTEND}/admin?tab=users", wait_until="domcontentloaded")
            expect(page.locator('[data-testid="user-search-input"]')).to_be_visible(timeout=30000)
            page.locator('[data-testid="user-search-input"]').fill(user_email)
            row = page.locator("tbody tr").filter(has_text=user_email)
            expect(row).to_be_visible(timeout=10000)
            row.locator('[data-testid^="view-user-"]').click()
            expect(page.locator('[data-testid="user-permissions-editor"]')).to_be_visible(timeout=10000)
            expect(page.locator('[data-testid="user-permission-groups"]')).to_contain_text(group_name)
            _select_searchable(page, "user-permission-allow", "Benutzer anlegen", "Benutzer anlegen")
            _select_searchable(page, "user-permission-deny", "Benutzer ansehen", "Benutzer ansehen")
            capture_page(page, "permissions", "04-benutzerrechte-ueberschreiben")
            page.locator('[data-testid="save-user-permissions"]').click()
            expect(page.get_by_text("Benutzerrechte aktualisiert")).to_be_visible(timeout=15000)

            detail = requests.get(f"{API}/admin/users/{user_id}", headers=headers, timeout=15).json()
            assert detail["group_ids"] == [group_id]
            assert detail["permission_overrides"] == {"allow": ["users.create"], "deny": ["users.view"]}
            assert "users.create" in detail["effective_permissions"]
            assert "users.view" not in detail["effective_permissions"]
            capture_page(page, "permissions", "05-gespeicherte-benutzerrechte")

            requests.delete(f"{API}/admin/users/{user_id}", headers=headers, timeout=15).raise_for_status()
            user_id = None
            page.keyboard.press("Escape")
            page.goto(f"{FRONTEND}/admin?tab=users", wait_until="domcontentloaded")
            expect(page.locator('[data-testid="show-permission-groups"]')).to_be_visible(timeout=60000)
            page.locator('[data-testid="show-permission-groups"]').click()
            expect(page.get_by_text(group_name, exact=True)).to_be_visible(timeout=10000)
            page.once("dialog", lambda dialog: dialog.accept())
            page.get_by_role("button", name=f"{group_name} löschen").click()
            expect(page.get_by_text("Nutzergruppe gelöscht")).to_be_visible(timeout=10000)
            expect(page.get_by_text(group_name, exact=True)).to_have_count(0)
            group_id = None
            capture_page(page, "permissions", "06-gruppe-geloescht")

            browser.close()
    finally:
        if user_id:
            requests.delete(f"{API}/admin/users/{user_id}", headers=headers, timeout=15)
        if group_id:
            requests.delete(f"{API}/admin/permission-groups/{group_id}", headers=headers, timeout=15)
