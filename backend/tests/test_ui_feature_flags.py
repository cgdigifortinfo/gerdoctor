"""Tests for the UI-Element feature-flags (phase 1 of upcoming rights system).

Covers:
  • PUT /api/admin/settings accepts the three new boolean keys
    (ui_show_journey_indicator / ui_show_eta_header / ui_show_progress_percentage)
  • GET /api/settings/public returns them without auth
  • PATCH with explicit `false` persists — not just `true` (regression for the
    `v is not None` filter that previously dropped false-y values).
"""
import os
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://guided-journey-5.preview.emergentagent.com").rstrip("/")
API = BASE + "/api"

ADMIN = {"email": "admin@example.com", "password": "Admin123!"}


@pytest.fixture(scope="module")
def admin_token():
    return requests.post(f"{API}/auth/login", json=ADMIN).json()["access_token"]


@pytest.fixture(scope="module")
def auth_h(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(autouse=True)
def _reset_after(auth_h):
    yield
    # Reset to defaults (all on) so dev experience stays unchanged
    requests.put(f"{API}/admin/settings", headers=auth_h,
                 json={"ui_show_journey_indicator": True,
                       "ui_show_eta_header": True,
                       "ui_show_progress_percentage": True})


class TestUIFeatureFlags:
    def test_accepts_all_three_flags(self, auth_h):
        r = requests.put(f"{API}/admin/settings", headers=auth_h,
                         json={"ui_show_journey_indicator": False,
                               "ui_show_eta_header": False,
                               "ui_show_progress_percentage": False})
        assert r.status_code == 200, r.text
        public = requests.get(f"{API}/settings/public").json()
        assert public["ui_show_journey_indicator"] is False
        assert public["ui_show_eta_header"] is False
        assert public["ui_show_progress_percentage"] is False

    def test_partial_update_only_changes_supplied_keys(self, auth_h):
        # Baseline: all True
        requests.put(f"{API}/admin/settings", headers=auth_h,
                     json={"ui_show_journey_indicator": True,
                           "ui_show_eta_header": True,
                           "ui_show_progress_percentage": True})
        # Turn off only the percentage
        requests.put(f"{API}/admin/settings", headers=auth_h,
                     json={"ui_show_progress_percentage": False})
        public = requests.get(f"{API}/settings/public").json()
        assert public["ui_show_journey_indicator"] is True
        assert public["ui_show_eta_header"] is True
        assert public["ui_show_progress_percentage"] is False

    def test_non_admin_cannot_update(self):
        r = requests.put(f"{API}/admin/settings",
                         json={"ui_show_journey_indicator": False})
        assert r.status_code in (401, 403)

    def test_public_endpoint_requires_no_auth(self):
        r = requests.get(f"{API}/settings/public")
        assert r.status_code == 200
        # Should always include the keys after phase-1 deployment
        assert "ui_show_journey_indicator" in r.json()
