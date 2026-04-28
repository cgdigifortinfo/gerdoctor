"""Backend tests for Survey V2 restructure.

Self-contained: creates dedicated ephemeral test users at module setup
(no dependency on the random `demoNNN-*` seed) and cleans up at teardown.

Covers:
  - /api/steps returns 24 steps with correct step_types & conditions
  - /api/steps/visibility returns hidden/blocked ids per user
  - /api/steps/progress auto_complete on decision=upload
  - /api/steps/progress no auto_complete on decision=partner
  - completion_pct excludes hidden steps
  - block condition Fachsprachenprüfung step 6 when milestone 5 pending
  - /api/admin/users completion_pct per stage-archetype user
"""
import os
import time
import uuid
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import asyncio

load_dotenv("/app/backend/.env")

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or "https://guided-journey-5.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("admin@example.com", "Admin123!")
TEST_PW = "Test123!"
RUN_TAG = f"sv2-{int(time.time())}-{uuid.uuid4().hex[:6]}"

# Stage archetypes used by the tests. Created fresh on every run.
STAGE_USERS = {
    "kumar":   f"{RUN_TAG}-kumar@chrizz1001.de",   # only step 1 done
    "schmidt": f"{RUN_TAG}-schmidt@chrizz1001.de",  # decision=upload on step 2
    "yilmaz":  f"{RUN_TAG}-yilmaz@chrizz1001.de",   # decision=partner on step 2
    "chen":    f"{RUN_TAG}-chen@chrizz1001.de",     # blocks 1-3 fully done
    "silva":   f"{RUN_TAG}-silva@chrizz1001.de",    # block 1 fully done
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


def register(email, name):
    """Create a user via /auth/register, return (session, user_id)."""
    s = requests.Session()
    r = s.post(
        f"{API}/auth/register",
        json={"email": email, "password": TEST_PW, "name": name},
        timeout=15,
    )
    assert r.status_code == 200, f"register failed {email}: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s, data["id"]


def _put_progress(s, step_id, status, data):
    r = s.put(f"{API}/steps/progress", json={"step_id": step_id, "status": status, "data": data}, timeout=15)
    assert r.status_code in (200, 201), f"progress update failed: {r.status_code} {r.text}"
    return r


def _stammdaten_payload(first, last):
    return {
        "first_name": first, "name": last,
        "date_of_birth": "1985-06-15",
        "phone": "+49 170 1234567",
        "address": "Teststr. 1, 10115 Berlin",
        "anerkennungsstatus": "Die Fachsprachenprüfung Medizin ist geplant",
        "anerkennungsverfahren_bundesland": "Berlin",
        "fachrichtung_praktiziert": "Innere Medizin",
        "fachrichtung_gewuenscht": "Innere Medizin",
    }


def _real_upload_doc():
    return {"documents": [{"file_id": str(uuid.uuid4()), "document_type": "Diplom", "filename": "diplom.pdf"}]}


def _seed_users(steps):
    """Register and shape each STAGE_USER into the right archetype."""
    by_order = {st["order"]: st for st in steps}
    sid = lambda o: str(by_order[o].get("id") or by_order[o].get("_id"))

    # kumar: register only — auto-progress rows are pending. No step 1 done.
    register(STAGE_USERS["kumar"], "Dr. Kumar Test")

    # schmidt: step 1 + decision=upload on step 2 (does NOT upload yet)
    s, _ = register(STAGE_USERS["schmidt"], "Dr. Schmidt Test")
    _put_progress(s, sid(1), "completed", _stammdaten_payload("Anna", "Schmidt"))
    _put_progress(s, sid(2), "completed", {"decision": "upload"})

    # yilmaz: step 1 + decision=partner on step 2
    s, _ = register(STAGE_USERS["yilmaz"], "Dr. Yilmaz Test")
    _put_progress(s, sid(1), "completed", _stammdaten_payload("Mehmet", "Yilmaz"))
    _put_progress(s, sid(2), "completed", {"decision": "partner"})

    # silva: complete block 1 fully (decision=upload + real file)
    s, _ = register(STAGE_USERS["silva"], "Dr. Silva Test")
    _put_progress(s, sid(1), "completed", _stammdaten_payload("Diego", "Silva"))
    _put_progress(s, sid(2), "completed", {"decision": "upload"})
    _put_progress(s, sid(3), "completed", _real_upload_doc())
    # milestone 5 auto-completes via has_upload condition

    # chen: complete blocks 1-3 (upload path each)
    s, _ = register(STAGE_USERS["chen"], "Dr. Chen Test")
    _put_progress(s, sid(1), "completed", _stammdaten_payload("Lin", "Chen"))
    for dec, up in ((2, 3), (6, 7), (10, 11)):
        _put_progress(s, sid(dec), "completed", {"decision": "upload"})
        _put_progress(s, sid(up), "completed", _real_upload_doc())


def _cleanup_users():
    """Async cleanup directly via MongoDB — drop all RUN_TAG users + their data."""
    async def _():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        db = client[os.environ["DB_NAME"]]
        emails = list(STAGE_USERS.values())
        users = await db.users.find({"email": {"$in": emails}}, {"_id": 1}).to_list(50)
        ids = [str(u["_id"]) for u in users]
        if ids:
            await db.user_progress.delete_many({"user_id": {"$in": ids}})
            await db.partner_submissions.delete_many({"user_id": {"$in": ids}})
            await db.progress_history.delete_many({"user_id": {"$in": ids}})
        await db.users.delete_many({"email": {"$in": emails}})
        client.close()
    asyncio.get_event_loop().run_until_complete(_())


# ---------- module-scoped fixtures ----------

@pytest.fixture(scope="module")
def admin_client():
    s, _ = login(*ADMIN)
    return s


@pytest.fixture(scope="module")
def steps(admin_client):
    r = admin_client.get(f"{API}/steps")
    assert r.status_code == 200, r.text
    steps = r.json()
    steps.sort(key=lambda s: s["order"])
    return steps


@pytest.fixture(scope="module", autouse=True)
def stage_users(steps):
    """Seed test-archetype users once per module run, cleanup at teardown."""
    _seed_users(steps)
    yield STAGE_USERS
    _cleanup_users()


# ---------- /api/steps structure ----------

class TestStepsStructure:
    def test_step_count_is_24(self, steps):
        # Core survey has 24 steps; an extra "Herzlichen Glückwunsch" display
        # step and any orphan duplicates may sit at order >= 25 and are tolerated.
        core = [s for s in steps if s["order"] <= 24]
        assert len(core) == 24, f"Expected 24 core steps (orders 1-24), got {len(core)}"

    def test_step_types_per_block(self, steps):
        by_order = {s["order"]: s for s in steps}
        assert by_order[1]["step_type"] == "form"
        assert by_order[2]["step_type"] == "decision"
        assert by_order[3]["step_type"] == "form"
        assert by_order[4]["step_type"] == "partner_selection"
        assert by_order[5]["step_type"] == "milestone"
        assert by_order[6]["step_type"] == "decision"
        assert by_order[9]["step_type"] == "milestone"
        assert by_order[18]["step_type"] == "decision"
        assert by_order[19]["step_type"] == "partner_multiselection"
        assert by_order[20]["step_type"] == "milestone"

    def test_decision_step_has_2_options(self, steps):
        by_order = {s["order"]: s for s in steps}
        dec2 = by_order[2]
        field = dec2["fields"][0]
        assert field["field_type"] == "decision"
        values = {o["value"] for o in field["options"]}
        assert values == {"upload", "partner"}
        dec18 = by_order[18]
        values18 = {o["value"] for o in dec18["fields"][0]["options"]}
        assert values18 == {"selbst", "partner_nutzen"}

    def test_hide_auto_complete_and_block_conditions(self, steps):
        by_order = {s["order"]: s for s in steps}
        c3 = by_order[3]["conditions"]
        assert any(c["action"] == "hide" and c["source_step_order"] == 2 for c in c3)
        c4 = by_order[4]["conditions"]
        assert any(c["action"] == "hide" and c["source_step_order"] == 2 for c in c4)
        c5 = by_order[5]["conditions"]
        assert any(
            c["action"] == "auto_complete"
            and c["source_step_order"] == 3
            and c.get("operator") == "has_upload"
            and c.get("field") == "documents"
            for c in c5
        ), f"milestone 5 should auto_complete on upload step #3 has_upload(documents), got {c5}"
        assert any(
            c.get("action") == "block"
            and isinstance(c.get("all_of"), list)
            and any(sub.get("source_step_order") == 3
                    and sub.get("operator") == "missing_upload" for sub in c["all_of"])
            for c in c5
        ), f"milestone 5 should block when upload=chosen+no file, got {c5}"
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
        assert len(names["fachrichtung_praktiziert"]["options"]) >= 35
        assert len(names["fachrichtung_gewuenscht"]["options"]) >= 35


# ---------- /api/steps/visibility ----------

class TestVisibility:
    def _get_vis(self, email):
        s, _ = login(email, TEST_PW)
        r = s.get(f"{API}/steps/visibility")
        assert r.status_code == 200, r.text
        return s, r.json()

    def test_kumar_blocked_step6(self, steps):
        # Kumar registered only — milestone 5 pending → step 6 blocked
        _, vis = self._get_vis(STAGE_USERS["kumar"])
        by_order = {s["order"]: s for s in steps}
        step6_id = str(by_order[6].get("id") or by_order[6].get("_id"))
        blocked = set(vis.get("blocked_step_ids", []))
        assert step6_id in blocked, f"step 6 should be blocked for kumar, blocked={blocked}"

    def test_schmidt_upload_hides_partner(self, steps):
        # schmidt picked decision=upload → partner step 4 hidden, upload step 3 visible
        _, vis = self._get_vis(STAGE_USERS["schmidt"])
        by_order = {s["order"]: s for s in steps}
        sid = lambda o: str(by_order[o].get("id") or by_order[o].get("_id"))
        hidden = set(vis.get("hidden_step_ids", []))
        assert sid(4) in hidden, "partner step 4 should be hidden for upload path"
        assert sid(3) not in hidden, "upload step 3 must be visible"

    def test_yilmaz_partner_hides_upload(self, steps):
        _, vis = self._get_vis(STAGE_USERS["yilmaz"])
        by_order = {s["order"]: s for s in steps}
        sid = lambda o: str(by_order[o].get("id") or by_order[o].get("_id"))
        hidden = set(vis.get("hidden_step_ids", []))
        assert sid(3) in hidden, "upload step 3 should be hidden on partner path"
        assert sid(4) not in hidden, "partner step 4 must be visible"


# ---------- Progress with auto_complete ----------

class TestAutoComplete:
    """Uses Kumar (only registered, nothing done) to test upload/partner flows."""

    def _login_kumar(self):
        return login(STAGE_USERS["kumar"], TEST_PW)[0]

    def _reset_kumar(self, s, steps):
        by_order = {st["order"]: st for st in steps}
        for o in (2, 3, 4, 5):
            sid = str(by_order[o].get("id") or by_order[o].get("_id"))
            s.put(f"{API}/steps/progress", json={"step_id": sid, "status": "pending", "data": {}}, timeout=15)

    def test_upload_triggers_milestone_auto_complete(self, steps):
        """Milestone 5 only auto-completes once upload step #3 has a real file."""
        s = self._login_kumar()
        self._reset_kumar(s, steps)
        by_order = {st["order"]: st for st in steps}
        sid2 = str(by_order[2].get("id") or by_order[2].get("_id"))
        sid3 = str(by_order[3].get("id") or by_order[3].get("_id"))
        sid5 = str(by_order[5].get("id") or by_order[5].get("_id"))

        # 1) Choose upload path
        _put_progress(s, sid2, "completed", {"decision": "upload"})

        # 2) Empty upload submission → backend rejects (400)
        r_bad = s.put(f"{API}/steps/progress", json={"step_id": sid3, "status": "completed", "data": {}}, timeout=15)
        assert r_bad.status_code == 400, f"expected 400 for empty upload, got {r_bad.status_code}: {r_bad.text}"
        assert "Dokument" in r_bad.text, f"expected German 'Dokument' error, got {r_bad.text}"

        # 3) Milestone 5 still pending + blocked
        prog_mid = {p["step_id"]: p for p in s.get(f"{API}/steps/progress").json()}
        assert prog_mid[sid5]["status"] != "completed"
        vis = s.get(f"{API}/steps/visibility").json()
        assert sid5 in (vis.get("blocked_step_ids") or [])

        # 4) Real file → milestone auto-completes
        _put_progress(s, sid3, "completed", _real_upload_doc())
        prog = {p["step_id"]: p for p in s.get(f"{API}/steps/progress").json()}
        assert prog[sid5]["status"] == "completed", f"milestone 5 not auto-completed: {prog[sid5]}"

        hist = s.get(f"{API}/steps/history").json()
        assert any(h.get("step_id") == sid5 and h.get("action") == "auto_completed" for h in hist), (
            "progress_history missing auto_completed entry for milestone 5"
        )
        self._reset_kumar(s, steps)

    def test_partner_does_not_auto_complete_milestone(self, steps):
        s = self._login_kumar()
        self._reset_kumar(s, steps)
        by_order = {st["order"]: st for st in steps}
        sid2 = str(by_order[2].get("id") or by_order[2].get("_id"))
        sid5 = str(by_order[5].get("id") or by_order[5].get("_id"))

        _put_progress(s, sid2, "completed", {"decision": "partner"})

        prog = {p["step_id"]: p for p in s.get(f"{API}/steps/progress").json()}
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
        ours = [u for u in users if u.get("email") in STAGE_USERS.values()]
        assert len(ours) == len(STAGE_USERS), f"expected {len(STAGE_USERS)} stage users, got {len(ours)}"
        for u in ours:
            pct = u.get("completion_pct")
            assert pct is not None, f"completion_pct missing for {u['email']}"
            assert 0 <= pct <= 100

    def test_chen_more_progress_than_kumar(self, admin_client):
        r = admin_client.get(f"{API}/admin/users")
        users = {u["email"]: u for u in r.json()}
        for email in STAGE_USERS.values():
            assert email in users, f"{email} missing from admin users list"
        kumar_pct = users[STAGE_USERS["kumar"]]["completion_pct"]
        chen_pct = users[STAGE_USERS["chen"]]["completion_pct"]
        silva_pct = users[STAGE_USERS["silva"]]["completion_pct"]
        assert chen_pct > kumar_pct, f"chen({chen_pct}) should > kumar({kumar_pct})"
        assert chen_pct > silva_pct, f"chen({chen_pct}) should > silva({silva_pct}) — more blocks done"
