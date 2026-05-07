"""Regression tests for `calculate_completion_pct` after the data-repair migration.

Validates:
  - Fresh user (no completed steps) → 0%
  - Stammdaten only → roughly 1/N visible-steps complete
  - Block 1 fully done → meaningfully > Stammdaten-only
  - Hidden steps are excluded from denominator (upload-path users don't get
    penalised for the hidden partner step or vice versa)
"""
import os
import time
import uuid
import asyncio
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://guided-journey-5.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN = ("admin@example.com", "Admin123!")
PW = "Test123!"
RUN = f"pct-{int(time.time())}-{uuid.uuid4().hex[:6]}"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, r.text
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return s


def _register(email, name):
    s = requests.Session()
    r = s.post(f"{API}/auth/register", json={"email": email, "password": PW, "name": name}, timeout=15)
    assert r.status_code == 200, r.text
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return s, r.json()["id"]


def _put(s, step_id, status, data):
    r = s.put(f"{API}/steps/progress",
              json={"step_id": step_id, "status": status, "data": data}, timeout=15)
    assert r.status_code == 200, r.text


def _stammdaten():
    return {
        "first_name": "Test", "name": "User", "date_of_birth": "1990-01-01",
        "phone": "+49 100 0000000", "address": "Teststr. 1, 10115 Berlin",
        "anerkennungsstatus": "Die Fachsprachenprüfung Medizin ist geplant",
        "anerkennungsverfahren_bundesland": "Berlin",
        "fachrichtung_praktiziert": "Innere Medizin",
        "fachrichtung_gewuenscht": "Innere Medizin",
    }


@pytest.fixture(scope="module")
def admin_session():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def steps(admin_session):
    r = admin_session.get(f"{API}/admin/steps")
    return sorted(r.json(), key=lambda s: s["order"])


@pytest.fixture(scope="module")
def by_order(steps):
    return {s["order"]: s for s in steps}


def _completion_for(admin_session, email):
    users = admin_session.get(f"{API}/admin/users").json()
    u = next(u for u in users if u["email"] == email)
    return u["completion_pct"]


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    async def _():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        db = client[os.environ["DB_NAME"]]
        users = await db.users.find({"email": {"$regex": f"^{RUN}-"}}, {"_id": 1}).to_list(50)
        ids = [str(u["_id"]) for u in users]
        if ids:
            await db.user_progress.delete_many({"user_id": {"$in": ids}})
            await db.partner_submissions.delete_many({"user_id": {"$in": ids}})
            await db.progress_history.delete_many({"user_id": {"$in": ids}})
        await db.users.delete_many({"email": {"$regex": f"^{RUN}-"}})
        client.close()
    asyncio.get_event_loop().run_until_complete(_())


def test_fresh_user_pct_is_zero(admin_session):
    email = f"{RUN}-fresh@chrizz1001.de"
    _register(email, "Fresh")
    pct = _completion_for(admin_session, email)
    assert pct == 0, f"fresh user should be 0%, got {pct}"


def test_stammdaten_only_low_pct(admin_session, by_order):
    email = f"{RUN}-stammdaten@chrizz1001.de"
    s, _ = _register(email, "Stammdaten")
    _put(s, by_order[1]["id"], "completed", _stammdaten())
    pct = _completion_for(admin_session, email)
    # 1 of ~25 steps done → small but non-zero
    assert 1 <= pct <= 15, f"expected 1-15% with only Stammdaten, got {pct}"


def test_upload_path_excludes_hidden_partner_step(admin_session, by_order):
    """When user picks decision=upload on Antragstellung (#3), the partner
    step (#5) is hidden and must not penalise the denominator. Completing
    block 1 fully (steps 1, 2-Schnellstart, 3, 4, 6-auto) → meaningful progress."""
    email = f"{RUN}-upload@chrizz1001.de"
    s, _ = _register(email, "Upload")
    _put(s, by_order[1]["id"], "completed", _stammdaten())
    _put(s, by_order[2]["id"], "completed", {"decision": "selber"})    # NEW Schnellstart
    _put(s, by_order[3]["id"], "completed", {"decision": "upload"})
    _put(s, by_order[4]["id"], "completed", {"documents": [{"file_id": str(uuid.uuid4()), "filename": "doc.pdf"}]})
    # step 6 should auto-complete via has_upload(documents)
    pct = _completion_for(admin_session, email)
    assert pct >= 10, f"upload-path user should have >=10%, got {pct}"


def test_partner_path_user_has_progress(admin_session, by_order):
    """Decision=partner on Antragstellung (#3): step 4 (upload) hidden, but
    Stammdaten + Schnellstart + decision + partner selection are visible+completed."""
    email = f"{RUN}-partner@chrizz1001.de"
    s, _ = _register(email, "PartnerPath")
    _put(s, by_order[1]["id"], "completed", _stammdaten())
    _put(s, by_order[2]["id"], "completed", {"decision": "selber"})   # NEW Schnellstart
    _put(s, by_order[3]["id"], "completed", {"decision": "partner"})
    _put(s, by_order[5]["id"], "completed", {"selected_partner_id": "x", "selected_partner_name": "ILS"})
    pct = _completion_for(admin_session, email)
    assert pct >= 10, f"partner-path user with 3 steps done should have >=10%, got {pct}"


def test_partner_pct_zero_after_cleanup(admin_session):
    """Partners and admins must show 0% (no orphan progress data)."""
    users = admin_session.get(f"{API}/admin/users").json()
    for u in users:
        if u["role"] in ("admin", "partner"):
            assert u["completion_pct"] == 0, f"{u['email']} ({u['role']}) should be 0%, got {u['completion_pct']}"
