"""Backend tests for Survey V2 restructure.

Covers:
  - /api/steps returns 24 steps with correct step_types & conditions
  - /api/steps/visibility returns hidden/blocked ids per user
  - /api/steps/progress auto_complete on decision=upload
  - /api/steps/progress no auto_complete on decision=partner
  - completion_pct / ETA excludes hidden steps
  - block condition Fachsprachenprüfung step 6 when milestone 5 pending
  - /api/admin/users completion_pct per demo user
"""
import os
import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or "https://guided-journey-5.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("admin@example.com", "Admin123!")
PARTNER = ("partner-example@chrizz1001.de", "Partner123!")
DEMO_PW = "Demo123!"
DEMO_USERS = {
    "schmidt": "dr.schmidt@chrizz1001.de",
    "yilmaz": "dr.yilmaz@chrizz1001.de",
    "chen": "dr.chen@chrizz1001.de",
    "kumar": "dr.kumar@chrizz1001.de",
    "silva": "dr.silva@chrizz1001.de",
}


def login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s, data


@pytest.fixture(scope="module")
def admin_client():
    s, _ = login(*ADMIN)
    return s


@pytest.fixture(scope="module")
def partner_client():
    s, _ = login(*PARTNER)
    return s


@pytest.fixture(scope="module")
def steps(admin_client):
    r = admin_client.get(f"{API}/steps")
    assert r.status_code == 200, r.text
    steps = r.json()
    steps.sort(key=lambda s: s["order"])
    return steps


# ---------- /api/steps structure ----------
class TestStepsStructure:
    def test_step_count_is_24(self, steps):
        assert len(steps) == 24, f"Expected 24 steps, got {len(steps)}"

    def test_step_types_per_block(self, steps):
        by_order = {s["order"]: s for s in steps}
        # Stammdaten
        assert by_order[1]["step_type"] == "form"
        # Block 1 Antragstellung
        assert by_order[2]["step_type"] == "decision"
        assert by_order[3]["step_type"] == "form"  # upload
        assert by_order[4]["step_type"] == "partner_selection"
        assert by_order[5]["step_type"] == "milestone"
        # Block 2 Fachsprachenprüfung
        assert by_order[6]["step_type"] == "decision"
        assert by_order[9]["step_type"] == "milestone"
        # Block 5 Jobangebote - no upload, multi partner
        assert by_order[18]["step_type"] == "decision"
        assert by_order[19]["step_type"] == "partner_multiselection"
        assert by_order[20]["step_type"] == "milestone"

    def test_decision_step_has_2_options(self, steps):
        by_order = {s["order"]: s for s in steps}
        dec2 = by_order[2]
        field = dec2["fields"][0]
        assert field["field_type"] == "decision"
        assert len(field["options"]) == 2
        values = {o["value"] for o in field["options"]}
        assert values == {"upload", "partner"}
        # Jobangebote decision: selbst / partner_nutzen
        dec18 = by_order[18]
        values18 = {o["value"] for o in dec18["fields"][0]["options"]}
        assert values18 == {"selbst", "partner_nutzen"}

    def test_hide_auto_complete_and_block_conditions(self, steps):
        by_order = {s["order"]: s for s in steps}
        # Upload step 3 hidden when decision 2 != upload
        c3 = by_order[3]["conditions"]
        assert any(c["action"] == "hide" and c["source_step_order"] == 2 for c in c3)
        # Partner step 4 hidden when 2 != partner
        c4 = by_order[4]["conditions"]
        assert any(c["action"] == "hide" and c["source_step_order"] == 2 for c in c4)
        # Milestone 5 auto_complete when upload step (#3) has a real file uploaded
        c5 = by_order[5]["conditions"]
        assert any(
            c["action"] == "auto_complete"
            and c["source_step_order"] == 3
            and c.get("operator") == "has_upload"
            and c.get("field") == "documents"
            for c in c5
        ), f"milestone 5 should auto_complete on upload step #3 has_upload(documents), got {c5}"
        # Milestone 5 must also block when user picked upload but uploaded nothing
        assert any(
            c.get("action") == "block"
            and isinstance(c.get("all_of"), list)
            and any(sub.get("source_step_order") == 3
                    and sub.get("operator") == "missing_upload" for sub in c["all_of"])
            for c in c5
        ), f"milestone 5 should block when upload=chosen+no file, got {c5}"
        # Fachsprachen decision step 6 blocked on milestone 5 status_not completed
        c6 = by_order[6]["conditions"]
        assert any(c["action"] == "block" and c["source_step_order"] == 5 for c in c6)

    def test_stammdaten_fields(self, steps):
        s1 = next(s for s in steps if s["order"] == 1)
        names = {f["name"]: f for f in s1["fields"]}
        for fname in ["date_of_birth", "anerkennungsstatus",
                       "anerkennungsverfahren_bundesland",
                       "fachrichtung_praktiziert", "fachrichtung_gewuenscht"]:
            assert fname in names, f"missing field {fname}"
        assert len(names["anerkennungsstatus"]["options"]) == 7
        assert len(names["anerkennungsverfahren_bundesland"]["options"]) == 16
        # Fachrichtungen list - from seed FACHRICHTUNGEN (35 items per current seed)
        assert len(names["fachrichtung_praktiziert"]["options"]) >= 35
        assert len(names["fachrichtung_gewuenscht"]["options"]) >= 35


# ---------- /api/steps/visibility ----------
class TestVisibility:
    def _get_vis(self, email):
        s, _ = login(email, DEMO_PW)
        r = s.get(f"{API}/steps/visibility")
        assert r.status_code == 200, r.text
        return s, r.json()

    def test_kumar_blocked_step6(self, steps):
        # Kumar only completed step1 -> milestone 5 is pending -> step 6 blocked
        _, vis = self._get_vis(DEMO_USERS["kumar"])
        by_order = {s["order"]: s for s in steps}
        step6_id = str(by_order[6]["id"]) if "id" in by_order[6] else str(by_order[6]["_id"])
        blocked = set(vis.get("blocked_step_ids", []))
        assert step6_id in blocked, f"step 6 should be blocked for kumar, blocked={blocked}"

    def test_schmidt_upload_hides_partner(self, steps):
        # schmidt chose decision2=upload -> partner step 4 hidden; upload step 3 visible
        _, vis = self._get_vis(DEMO_USERS["schmidt"])
        by_order = {s["order"]: s for s in steps}

        def sid(o):
            return str(by_order[o].get("id") or by_order[o].get("_id"))
        hidden = set(vis.get("hidden_step_ids", []))
        assert sid(4) in hidden, "partner step 4 should be hidden for upload path"
        assert sid(3) not in hidden, "upload step 3 must be visible"

    def test_yilmaz_partner_hides_upload(self, steps):
        _, vis = self._get_vis(DEMO_USERS["yilmaz"])
        by_order = {s["order"]: s for s in steps}

        def sid(o):
            return str(by_order[o].get("id") or by_order[o].get("_id"))
        hidden = set(vis.get("hidden_step_ids", []))
        assert sid(3) in hidden, "upload step 3 should be hidden on partner path"
        assert sid(4) not in hidden, "partner step 4 must be visible"


# ---------- Progress with auto_complete ----------
class TestAutoComplete:
    """Uses Kumar (only step1 done, no decisions yet) to test upload/partner flows."""

    def _login_kumar(self):
        return login(DEMO_USERS["kumar"], DEMO_PW)[0]

    def _reset_kumar(self, s, steps):
        """Reset step 2 and 5 back to pending."""
        by_order = {st["order"]: st for st in steps}
        for o in (2, 3, 4, 5):
            sid = str(by_order[o].get("id") or by_order[o].get("_id"))
            s.put(f"{API}/steps/progress", json={
                "step_id": sid, "status": "pending", "data": {}
            }, timeout=15)

    def test_upload_triggers_milestone_auto_complete(self, steps):
        """Milestone 5 only auto-completes once the upload step (#3) has a real file.
        The backend now rejects empty upload submissions outright, and the milestone
        stays blocked until a real file is uploaded."""
        s = self._login_kumar()
        self._reset_kumar(s, steps)
        by_order = {st["order"]: st for st in steps}
        sid2 = str(by_order[2].get("id") or by_order[2].get("_id"))
        sid3 = str(by_order[3].get("id") or by_order[3].get("_id"))
        sid5 = str(by_order[5].get("id") or by_order[5].get("_id"))

        # 1) Choose upload path on decision step
        r = s.put(f"{API}/steps/progress", json={
            "step_id": sid2, "status": "completed", "data": {"decision": "upload"}
        }, timeout=15)
        assert r.status_code in (200, 201), r.text

        # 2) Try to complete upload step WITHOUT any files → backend must reject (400)
        r_bad = s.put(f"{API}/steps/progress", json={
            "step_id": sid3, "status": "completed", "data": {}
        }, timeout=15)
        assert r_bad.status_code == 400, f"expected 400 for empty upload, got {r_bad.status_code}: {r_bad.text}"
        assert "Dokument" in r_bad.text, f"expected German 'Dokument' error, got {r_bad.text}"

        # 3) Milestone 5 must still be pending AND blocked (visibility endpoint)
        r_mid = s.get(f"{API}/steps/progress")
        prog_mid = {p["step_id"]: p for p in r_mid.json()}
        assert prog_mid[sid5]["status"] != "completed", (
            f"milestone 5 must NOT auto-complete without a real file, got {prog_mid[sid5]}"
        )
        vis = s.get(f"{API}/steps/visibility").json()
        assert sid5 in (vis.get("blocked_step_ids") or []), (
            f"milestone 5 must be blocked when upload path chosen but no file, got {vis}"
        )

        # 4) Upload a real file → milestone auto-completes
        r = s.put(f"{API}/steps/progress", json={
            "step_id": sid3, "status": "completed",
            "data": {"documents": [
                {"file_id": "test-file", "document_type": "Diplom",
                 "filename": "diplom.pdf"}
            ]}
        }, timeout=15)
        assert r.status_code in (200, 201), r.text

        r2 = s.get(f"{API}/steps/progress")
        prog = {p["step_id"]: p for p in r2.json()}
        assert sid5 in prog, "milestone 5 progress missing"
        assert prog[sid5]["status"] == "completed", f"milestone 5 not auto-completed: {prog[sid5]}"

        hist = s.get(f"{API}/steps/history").json()
        assert any(h.get("step_id") == sid5 and h.get("action") == "auto_completed" for h in hist), (
            "progress_history missing auto_completed entry for milestone 5"
        )
        # reset afterwards
        self._reset_kumar(s, steps)

    def test_partner_does_not_auto_complete_milestone(self, steps):
        s = self._login_kumar()
        self._reset_kumar(s, steps)
        by_order = {st["order"]: st for st in steps}
        sid2 = str(by_order[2].get("id") or by_order[2].get("_id"))
        sid5 = str(by_order[5].get("id") or by_order[5].get("_id"))

        r = s.put(f"{API}/steps/progress", json={
            "step_id": sid2, "status": "completed", "data": {"decision": "partner"}
        }, timeout=15)
        assert r.status_code in (200, 201), r.text

        r2 = s.get(f"{API}/steps/progress")
        prog = {p["step_id"]: p for p in r2.json()}
        assert sid5 in prog
        assert prog[sid5]["status"] != "completed", (
            f"milestone 5 should NOT auto-complete on partner path: {prog[sid5]}"
        )
        self._reset_kumar(s, steps)


# ---------- Completion pct / ETA ----------
class TestCompletionMetrics:
    def test_admin_users_have_completion_pct(self, admin_client):
        r = admin_client.get(f"{API}/admin/users")
        assert r.status_code == 200, r.text
        users = r.json()
        demo = [u for u in users if u.get("email", "").endswith("@chrizz1001.de")]
        assert len(demo) >= 5, f"expected 5 demo users in admin list, got {len(demo)}"
        for u in demo:
            pct = u.get("completion_pct")
            assert pct is not None, f"completion_pct missing for {u['email']}"
            assert 0 <= pct <= 100

    def test_upload_vs_partner_progress_differ_or_consistent(self, admin_client):
        # Both paths should hide the other, so denominator differs but pct is in [0,100].
        r = admin_client.get(f"{API}/admin/users")
        users = {u["email"]: u for u in r.json() if u.get("email", "").endswith("@chrizz1001.de")}
        for email in DEMO_USERS.values():
            assert email in users, f"{email} missing"
        # Kumar: only step 1 done -> low pct
        kumar_pct = users[DEMO_USERS["kumar"]]["completion_pct"]
        # chen: up to step 13 -> higher
        chen_pct = users[DEMO_USERS["chen"]]["completion_pct"]
        assert chen_pct > kumar_pct, f"chen({chen_pct}) should > kumar({kumar_pct})"
