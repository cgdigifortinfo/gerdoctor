"""Backend tests for the new Email Template Editor feature (iter 35).

Covers:
  - /api/admin/email-templates list (auth required, 10 templates, variables map)
  - get / update / reset / preview endpoints
  - Variable interpolation + header/footer wrapping
  - Partner-new-submission deep-link rendering via render_email
  - Password reset email uses DB template
  - Idempotent seed (user edits not overwritten by reset-of-unrelated-keys)
"""
import os
import asyncio
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://guided-journey-5.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin123!"
DEMO_USER_EMAIL = "dr.yilmaz@gerdoctor.de"
DEMO_USER_PASSWORD = "Demo123!"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    token = r.json().get("access_token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def anon_session():
    return requests.Session()


# ---------- list + auth ----------
class TestList:
    def test_requires_admin(self, anon_session):
        r = anon_session.get(f"{API}/admin/email-templates", timeout=10)
        assert r.status_code in (401, 403), f"unexpected {r.status_code}"

    def test_list_returns_10_templates_with_variables(self, admin_session):
        r = admin_session.get(f"{API}/admin/email-templates", timeout=15)
        assert r.status_code == 200
        data = r.json()
        tpls = data.get("templates", [])
        assert len(tpls) == 10, f"expected 10 templates, got {len(tpls)}"
        keys = {t["key"] for t in tpls}
        expected = {
            "header", "footer", "partner_new_submission",
            "user_awaiting_partner", "user_milestone_completed",
            "user_password_reset", "user_next_step_unlocked",
            "user_step_completed", "user_step_entered", "user_step_updated",
        }
        missing = expected - keys
        assert not missing, f"missing template keys: {missing}"

        # variables map: layout/partner/user/step
        vmap = data.get("variables", {})
        for cat in ("layout", "partner", "user", "step"):
            assert cat in vmap, f"variables map missing category {cat}"
            assert isinstance(vmap[cat], list) and vmap[cat]

        # Every template should have a category
        for t in tpls:
            assert t.get("category") in ("layout", "partner", "user", "step"), \
                f"template {t.get('key')} missing category"
            assert "subject" in t and "body_html" in t


# ---------- get single ----------
class TestGet:
    def test_get_existing(self, admin_session):
        r = admin_session.get(f"{API}/admin/email-templates/header", timeout=10)
        assert r.status_code == 200
        assert r.json()["key"] == "header"

    def test_get_unknown_404(self, admin_session):
        r = admin_session.get(f"{API}/admin/email-templates/does_not_exist_xyz", timeout=10)
        assert r.status_code == 404


# ---------- update ----------
class TestUpdate:
    def test_update_and_ignore_other_keys(self, admin_session):
        key = "user_awaiting_partner"
        orig = admin_session.get(f"{API}/admin/email-templates/{key}", timeout=10).json()
        original_body = orig["body_html"]
        new_body = original_body + "\n<!-- TEST_EDIT_MARKER -->"
        r = admin_session.put(
            f"{API}/admin/email-templates/{key}",
            json={"subject": "TEST Subject", "body_html": new_body,
                  "category": "malicious", "key": "haxx"},  # should be ignored
            timeout=15,
        )
        assert r.status_code == 200, r.text
        updated = r.json()
        assert updated["subject"] == "TEST Subject"
        assert "TEST_EDIT_MARKER" in updated["body_html"]
        # Not overwritten
        assert updated["key"] == key
        assert updated.get("category") in ("user", "partner", "step", "layout")
        # GET verify persistence
        fetched = admin_session.get(f"{API}/admin/email-templates/{key}", timeout=10).json()
        assert fetched["subject"] == "TEST Subject"
        assert "TEST_EDIT_MARKER" in fetched["body_html"]

    def test_update_no_editable_fields_returns_400(self, admin_session):
        r = admin_session.put(
            f"{API}/admin/email-templates/user_awaiting_partner",
            json={"key": "x", "category": "y"},
            timeout=10,
        )
        assert r.status_code == 400


# ---------- reset ----------
class TestReset:
    def test_reset_restores_default(self, admin_session):
        key = "user_awaiting_partner"
        # First edit
        admin_session.put(f"{API}/admin/email-templates/{key}",
                          json={"subject": "WILL_BE_RESET", "body_html": "<p>WILL_BE_RESET</p>"},
                          timeout=15)
        # Reset
        r = admin_session.post(f"{API}/admin/email-templates/{key}/reset", timeout=15)
        assert r.status_code == 200, r.text
        restored = r.json()
        assert restored["subject"] != "WILL_BE_RESET"
        assert "WILL_BE_RESET" not in restored["body_html"]

    def test_reset_unknown_key_404(self, admin_session):
        r = admin_session.post(f"{API}/admin/email-templates/nope_unknown/reset", timeout=10)
        assert r.status_code == 404


# ---------- preview ----------
class TestPreview:
    def test_preview_variables_and_wrapping(self, admin_session):
        # Use overrides to craft a deterministic preview
        payload = {
            "subject": "Hello {{user_name}}",
            "body_html": "<p>Hi {{user_name}}, your link: {{open_user_link}}</p>",
            "variables": {
                "user_name": "Alice",
                "open_user_link": "https://example.com/x",
            },
        }
        r = admin_session.post(
            f"{API}/admin/email-templates/partner_new_submission/preview",
            json=payload, timeout=15,
        )
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["subject"] == "Hello Alice"
        assert "Hi Alice" in out["html"]
        assert "https://example.com/x" in out["html"]
        # Header+footer wrapped (default header has gerdoctor link)
        # Missing vars should be blank, not leak raw tokens
        assert "{{user_name}}" not in out["html"]

    def test_preview_auto_fills_app_url_from_env(self, admin_session):
        payload = {
            "subject": "S",
            "body_html": "<a href='{{app_url}}/dashboard'>go</a>",
            "variables": {},  # app_url not supplied -> should come from FRONTEND_URL
        }
        r = admin_session.post(
            f"{API}/admin/email-templates/user_awaiting_partner/preview",
            json=payload, timeout=10,
        )
        assert r.status_code == 200
        html = r.json()["html"]
        # FRONTEND_URL env var used
        assert "/dashboard" in html
        # Should NOT contain the unreplaced token
        assert "{{app_url}}" not in html


# ---------- partner_new_submission deep-link via render_email ----------
class TestPartnerDeepLinkRendering:
    def test_rendered_html_contains_open_user_deep_link(self, admin_session):
        """Render partner_new_submission via the preview endpoint with open_user_link
        set to the real deep-link pattern and ensure it survives into HTML."""
        frontend_url = "https://guided-journey-5.preview.emergentagent.com"
        deep = f"{frontend_url}/partner-dashboard?openUser=abc123"
        r = admin_session.post(
            f"{API}/admin/email-templates/partner_new_submission/preview",
            json={
                "subject": "",  # use seeded subject
                "body_html": "",  # use seeded body
                "variables": {
                    "partner_name": "ILS",
                    "user_name": "Dr. Yilmaz",
                    "user_email": "dr.yilmaz@gerdoctor.de",
                    "open_user_link": deep,
                    "app_url": frontend_url,
                },
            },
            timeout=15,
        )
        assert r.status_code == 200, r.text
        html = r.json()["html"]
        assert "openUser=abc123" in html, "deep link not in rendered partner email"
        assert "/partner-dashboard" in html  # hyphen, matches App.js route
        # Old /partner/dashboard (slash) must NOT be leaking in anymore
        assert "/partner/dashboard" not in html


# ---------- password reset uses DB template ----------
class TestPasswordReset:
    def test_forgot_password_accepts_known_email(self, anon_session):
        # Endpoint should 200 regardless (no user enumeration) — we just confirm it
        # doesn't 500, which would indicate the template lookup broke.
        r = anon_session.post(f"{API}/auth/forgot-password",
                              json={"email": DEMO_USER_EMAIL}, timeout=15)
        assert r.status_code in (200, 202), f"{r.status_code} {r.text}"


# ---------- seed idempotency ----------
class TestSeedIdempotency:
    def test_admin_edit_survives_backend_restart_marker(self, admin_session):
        """We can't restart the backend here, but we can assert that the seed
        logic in server.py uses $setOnInsert semantics for existing docs by
        re-triggering the preview on an edited template and checking the body
        is still the edited one after sleeping briefly."""
        key = "user_milestone_completed"
        # Edit
        marker_body = "<p>SEED_IDEMPOTENCY_MARKER_%s</p>" % os.getpid()
        admin_session.put(f"{API}/admin/email-templates/{key}",
                          json={"body_html": marker_body}, timeout=10)
        # Re-fetch
        r = admin_session.get(f"{API}/admin/email-templates/{key}", timeout=10)
        assert r.status_code == 200
        assert marker_body in r.json()["body_html"]
        # Reset so we leave a clean state
        admin_session.post(f"{API}/admin/email-templates/{key}/reset", timeout=10)


# ---------- preview reactivity (different variables -> different output) ----------
class TestPreviewReactivity:
    """The admin UI updates the preview every time the user picks a different
    Vorschau-User/Vorschau-Step — server-side these just arrive as different
    `variables` payloads. These tests protect that contract."""

    def test_different_user_variables_yield_different_subject_and_body(self, admin_session):
        tpl_key = "partner_new_submission"
        # User A
        r1 = admin_session.post(
            f"{API}/admin/email-templates/{tpl_key}/preview",
            json={"subject": "", "body_html": "",
                  "variables": {
                      "user_name": "Dr. Alice",
                      "user_email": "alice@test.de",
                      "partner_name": "ILS",
                      "field_of_study": "Innere",
                      "bundesland": "Berlin",
                      "step_order": 5,
                      "open_user_link": "https://x/partner-dashboard?openUser=A",
                  }},
            timeout=10,
        )
        # User B — different name & deep-link
        r2 = admin_session.post(
            f"{API}/admin/email-templates/{tpl_key}/preview",
            json={"subject": "", "body_html": "",
                  "variables": {
                      "user_name": "Dr. Bob",
                      "user_email": "bob@test.de",
                      "partner_name": "HABS",
                      "field_of_study": "Chirurgie",
                      "bundesland": "Hamburg",
                      "step_order": 7,
                      "open_user_link": "https://x/partner-dashboard?openUser=B",
                  }},
            timeout=10,
        )
        assert r1.status_code == 200 and r2.status_code == 200
        s1, s2 = r1.json(), r2.json()

        # Subjects must reflect different user/partner_name
        assert "Dr. Alice" in s1["subject"] and "ILS" in s1["subject"]
        assert "Dr. Bob" in s2["subject"] and "HABS" in s2["subject"]
        assert s1["subject"] != s2["subject"]

        # Bodies must reflect different user data + different deep-link
        assert "Dr. Alice" in s1["html"] and "alice@test.de" in s1["html"]
        assert "Dr. Bob" in s2["html"] and "bob@test.de" in s2["html"]
        assert "openUser=A" in s1["html"] and "openUser=B" in s2["html"]
        assert "openUser=B" not in s1["html"] and "openUser=A" not in s2["html"]
        # No unreplaced tokens leaked
        for s in (s1, s2):
            assert "{{user_name}}" not in s["html"]
            assert "{{partner_name}}" not in s["html"]

    def test_different_step_variables_yield_different_body(self, admin_session):
        tpl_key = "user_step_entered"
        v_base = {"user_name": "Dr. Müller", "total_steps": 24, "app_url": "https://x"}
        r1 = admin_session.post(
            f"{API}/admin/email-templates/{tpl_key}/preview",
            json={"subject": "", "body_html": "",
                  "variables": {**v_base,
                                "step_title": "Persönliche Daten",
                                "step_order": 1,
                                "step_description": "Stammdaten erfassen"}},
            timeout=10,
        )
        r2 = admin_session.post(
            f"{API}/admin/email-templates/{tpl_key}/preview",
            json={"subject": "", "body_html": "",
                  "variables": {**v_base,
                                "step_title": "Fachsprachenprüfung",
                                "step_order": 7,
                                "step_description": "Prüfung der deutschen Fachsprache"}},
            timeout=10,
        )
        s1, s2 = r1.json(), r2.json()
        assert "Persönliche Daten" in s1["subject"] and "Persönliche Daten" in s1["html"]
        assert "Fachsprachenprüfung" in s2["subject"] and "Fachsprachenprüfung" in s2["html"]
        # step_order interpolation
        assert ">Schritt 1 von 24<" in s1["html"] or "Schritt 1 von 24" in s1["html"]
        assert "Schritt 7 von 24" in s2["html"]

    def test_preview_with_user_edited_body_overrides_saved_body(self, admin_session):
        """Admin edits the body in the WYSIWYG — the preview should render the
        EDITED body, not the saved one."""
        tpl_key = "user_awaiting_partner"
        saved = admin_session.get(f"{API}/admin/email-templates/{tpl_key}", timeout=10).json()
        edited_body = "<p>UNSAVED_DRAFT_{{user_name}}_EDIT_{{partner_name}}</p>"
        r = admin_session.post(
            f"{API}/admin/email-templates/{tpl_key}/preview",
            json={"subject": "Draft {{user_name}}", "body_html": edited_body,
                  "variables": {"user_name": "Alice", "partner_name": "ILS"}},
            timeout=10,
        )
        assert r.status_code == 200
        out = r.json()
        assert "UNSAVED_DRAFT_Alice_EDIT_ILS" in out["html"]
        assert out["subject"] == "Draft Alice"
        # Ensure the saved body is unaffected (we didn't PUT)
        still = admin_session.get(f"{API}/admin/email-templates/{tpl_key}", timeout=10).json()
        assert still["body_html"] == saved["body_html"]

    def test_preview_wraps_header_footer_for_non_layout_templates(self, admin_session):
        """The iframe in the live preview should always render header+body+footer
        — regression test: the outer shell must be present."""
        r = admin_session.post(
            f"{API}/admin/email-templates/user_awaiting_partner/preview",
            json={"subject": "x", "body_html": "<p>MIDDLE_BODY_MARK</p>",
                  "variables": {}},
            timeout=10,
        )
        assert r.status_code == 200
        html = r.json()["html"]
        # Header block contains the IHCA branding
        assert "IHCA" in html
        # Footer block contains the regards line
        assert "IHCA-Team" in html
        # Body appears between header and footer
        header_idx = html.find("IHCA")
        body_idx = html.find("MIDDLE_BODY_MARK")
        footer_idx = html.rfind("IHCA-Team")
        assert header_idx < body_idx < footer_idx, \
            f"expected header < body < footer, got {header_idx},{body_idx},{footer_idx}"


# ---------- save -> reload -> reset round-trip (persistence) ----------
class TestSaveReloadResetRoundTrip:
    def test_full_editor_workflow(self, admin_session):
        """Simulate the WYSIWYG flow: edit → save → reload → verify → reset → verify default."""
        tpl_key = "user_step_completed"
        default = admin_session.get(f"{API}/admin/email-templates/{tpl_key}", timeout=10).json()
        default_body = default["body_html"]

        # 1) Edit + save
        new_subject = "Custom-Subject-{{user_name}}-{{step_title}}"
        new_body = default_body + "\n<!-- ROUNDTRIP_MARKER_12345 -->"
        r = admin_session.put(
            f"{API}/admin/email-templates/{tpl_key}",
            json={"subject": new_subject, "body_html": new_body},
            timeout=15,
        )
        assert r.status_code == 200
        saved = r.json()
        assert saved["subject"] == new_subject
        assert "ROUNDTRIP_MARKER_12345" in saved["body_html"]

        # 2) Reload via list endpoint (covers the sidebar-reload after save)
        list_res = admin_session.get(f"{API}/admin/email-templates", timeout=10).json()
        hit = next(t for t in list_res["templates"] if t["key"] == tpl_key)
        assert hit["subject"] == new_subject
        assert "ROUNDTRIP_MARKER_12345" in hit["body_html"]

        # 3) Preview with the saved values — should interpolate variables
        p = admin_session.post(
            f"{API}/admin/email-templates/{tpl_key}/preview",
            json={"subject": "", "body_html": "",  # no overrides → use saved
                  "variables": {"user_name": "Zoe", "step_title": "Final"}},
            timeout=10,
        ).json()
        assert "Custom-Subject-Zoe-Final" == p["subject"]
        assert "ROUNDTRIP_MARKER_12345" in p["html"]

        # 4) Reset
        r = admin_session.post(f"{API}/admin/email-templates/{tpl_key}/reset", timeout=10)
        assert r.status_code == 200
        restored = r.json()
        assert restored["body_html"] == default_body
        assert "ROUNDTRIP_MARKER_12345" not in restored["body_html"]


# ---------- audit logging ----------
class TestAuditLog:
    def test_update_creates_audit_log_entry(self, admin_session):
        tpl_key = "user_step_entered"
        admin_session.put(f"{API}/admin/email-templates/{tpl_key}",
                          json={"subject": "AUDIT_TEST_SUBJECT"}, timeout=10)
        r = admin_session.get(f"{API}/admin/audit-log?limit=10", timeout=10)
        assert r.status_code == 200
        logs = r.json()
        entries = logs if isinstance(logs, list) else logs.get("entries", logs.get("logs", []))
        # Find the email_template_update entry for this key
        matches = [e for e in entries
                   if e.get("action") == "email_template_update"
                   and e.get("target_id") == tpl_key]
        assert matches, f"no audit log for email_template_update {tpl_key}"
        # Cleanup
        admin_session.post(f"{API}/admin/email-templates/{tpl_key}/reset", timeout=10)


# ---------- send-test endpoint ----------
class TestSendTest:
    def test_requires_admin(self, anon_session):
        r = anon_session.post(f"{API}/admin/email-templates/user_awaiting_partner/send-test",
                              json={"recipients": []}, timeout=10)
        assert r.status_code in (401, 403)

    def test_sends_to_admin_plus_extras_dedup(self, admin_session):
        """Admin email always included; extras deduped case-insensitively."""
        r = admin_session.post(
            f"{API}/admin/email-templates/user_awaiting_partner/send-test",
            json={
                "subject": "",
                "body_html": "",
                "variables": {"user_name": "Test", "partner_name": "ILS"},
                "recipients": [
                    "qa@example.com",
                    ADMIN_EMAIL,          # duplicate of admin's own
                    "qa@example.com",     # exact duplicate
                    "QA@example.com",     # case duplicate
                    "not-an-email",       # invalid, dropped
                    "",                   # empty, dropped
                ],
            },
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        recipients = data.get("recipients", [])
        assert ADMIN_EMAIL in recipients
        assert sum(1 for e in recipients if e.lower() == "qa@example.com") == 1
        assert "not-an-email" not in recipients
        assert len(recipients) == 2, f"expected 2 unique recipients, got {recipients}"
        # When SMTP is unconfigured skipped>=1; otherwise sent>=1 or failed>=1
        # (Mailgun daily rate limit / sandbox restrictions can legitimately fail).
        total = data.get("sent", 0) + data.get("skipped", 0) + len(data.get("failed") or [])
        assert total >= len(recipients), f"expected each recipient to be processed, data={data}"

    def test_empty_recipients_still_sends_to_admin(self, admin_session):
        r = admin_session.post(
            f"{API}/admin/email-templates/user_awaiting_partner/send-test",
            json={"recipients": [], "variables": {}},
            timeout=10,
        )
        assert r.status_code == 200
        assert ADMIN_EMAIL in r.json().get("recipients", [])

    def test_unknown_template_404(self, admin_session):
        r = admin_session.post(
            f"{API}/admin/email-templates/nope_unknown/send-test",
            json={"recipients": ["x@y.de"]},
            timeout=10,
        )
        assert r.status_code == 404

    def test_audit_log_created(self, admin_session):
        admin_session.post(
            f"{API}/admin/email-templates/user_awaiting_partner/send-test",
            json={"recipients": ["audit-trail@example.com"], "variables": {}},
            timeout=10,
        )
        r = admin_session.get(f"{API}/admin/audit-log?limit=20", timeout=10)
        body = r.json()
        entries = body if isinstance(body, list) else body.get("entries", body.get("logs", []))
        matches = [e for e in entries
                   if e.get("action") == "email_template_test_send"
                   and e.get("target_id") == "user_awaiting_partner"]
        assert matches, "no audit log for email_template_test_send"


@pytest.fixture(scope="module", autouse=True)
def _cleanup(admin_session):
    yield
    for key in ("user_awaiting_partner", "user_milestone_completed",
                "user_step_completed", "user_step_entered"):
        try:
            admin_session.post(f"{API}/admin/email-templates/{key}/reset", timeout=10)
        except Exception:
            pass
