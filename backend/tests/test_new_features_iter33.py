"""Iteration 33 – Tests for 4 new features on top of Survey v2:
(1) Anerkennungsstatus auto-skip of whole theme blocks
(2) CMS Landing feature boxes (box1..3) DE/EN
(3) Step Template library CRUD + apply
(4) (UI-only; skipped here)

Self-contained: registers ephemeral users at module setup, cleans up after.
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

ADMIN = {"email": "admin@example.com", "password": "Admin123!"}
USER_PW = "Test123!"
RUN_TAG = f"iter33-{int(time.time())}-{uuid.uuid4().hex[:6]}"

# Ephemeral user roles for the tests below.
TEST_USERS = {
    "petrov":  f"{RUN_TAG}-petrov@chrizz1001.de",
    "tanaka":  f"{RUN_TAG}-tanaka@chrizz1001.de",
    "ahmed":   f"{RUN_TAG}-ahmed@chrizz1001.de",
    "kumar":   f"{RUN_TAG}-kumar@chrizz1001.de",
}


def login(session, email, password):
    r = session.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    token = r.json()["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})
    return r.json()


def _register(email, name):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/register", json={"email": email, "password": USER_PW, "name": name})
    assert r.status_code == 200, f"register failed {email}: {r.status_code} {r.text}"
    token = r.json()["access_token"]
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


# ---------- shared fixtures ----------
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    login(s, ADMIN["email"], ADMIN["password"])
    return s


@pytest.fixture(scope="module")
def steps_by_order(admin_session):
    r = admin_session.get(f"{API}/admin/steps")
    assert r.status_code == 200
    steps = r.json()
    return {s["order"]: s for s in steps}


@pytest.fixture(scope="module", autouse=True)
def ephemeral_users():
    """Create ephemeral users once per module run, cleanup at teardown."""
    for key, email in TEST_USERS.items():
        _register(email, f"Iter33 {key.title()}")
    yield TEST_USERS

    async def _cleanup():
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        db = client[os.environ["DB_NAME"]]
        emails = list(TEST_USERS.values())
        users = await db.users.find({"email": {"$in": emails}}, {"_id": 1}).to_list(50)
        ids = [str(u["_id"]) for u in users]
        if ids:
            await db.user_progress.delete_many({"user_id": {"$in": ids}})
            await db.partner_submissions.delete_many({"user_id": {"$in": ids}})
            await db.progress_history.delete_many({"user_id": {"$in": ids}})
        await db.users.delete_many({"email": {"$in": emails}})
        client.close()
    asyncio.get_event_loop().run_until_complete(_cleanup())


def reset_user_progress(admin_session, email):
    """Reset a user's progress to pending via direct admin progress updates."""
    users = admin_session.get(f"{API}/admin/users").json()
    user = next((u for u in users if u["email"] == email), None)
    assert user, f"user {email} not found"
    user_id = user["id"]
    steps = admin_session.get(f"{API}/admin/steps").json()
    for s in steps:
        admin_session.put(
            f"{API}/admin/users/{user_id}/progress",
            json={"step_id": s["id"], "status": "pending", "data": {}},
        )
    return user_id


# ==========================================================
# Feature 1 — Anerkennungsstatus auto-skip
# ==========================================================
def _step1_payload(anerk: str):
    return {
        "first_name": "Test", "name": "User", "date_of_birth": "1980-01-01",
        "phone": "+49 0 0000000", "address": "Teststr. 1",
        "anerkennungsstatus": anerk,
        "anerkennungsverfahren_bundesland": "Bayern",
        "fachrichtung_praktiziert": "Allgemeinmedizin",
        "fachrichtung_gewuenscht": "Allgemeinmedizin",
    }


@pytest.mark.parametrize("user_key,anerk,expected_completed,expected_auto_skip_count", [
    ("petrov", "Ich bin in Deutschland approbiert", 13, 12),
    ("tanaka", "Ich habe die Fachsprachenprüfung Medizin bestanden", 4, 3),
])
def test_anerkennungsstatus_autoskip(admin_session, steps_by_order, user_key, anerk, expected_completed, expected_auto_skip_count):
    email = TEST_USERS[user_key]
    reset_user_progress(admin_session, email)
    step1_id = steps_by_order[1]["id"]

    us = requests.Session(); us.headers.update({"Content-Type": "application/json"})
    login(us, email, USER_PW)

    r = us.put(f"{API}/steps/progress", json={
        "step_id": step1_id, "status": "completed",
        "data": _step1_payload(anerk),
    })
    assert r.status_code == 200, f"step1 update failed: {r.status_code} {r.text}"

    progress = us.get(f"{API}/steps/progress").json()
    completed = [p for p in progress if p["status"] == "completed"]
    auto_skipped = [p for p in completed if (p.get("data") or {}).get("auto_skipped_by_status") is True]
    assert len(completed) == expected_completed, f"expected {expected_completed} completed, got {len(completed)}"
    assert len(auto_skipped) == expected_auto_skip_count, f"expected {expected_auto_skip_count} auto_skipped, got {len(auto_skipped)}"


def test_anerkennungsstatus_no_skip(admin_session, steps_by_order):
    email = TEST_USERS["ahmed"]
    reset_user_progress(admin_session, email)
    step1_id = steps_by_order[1]["id"]

    us = requests.Session(); us.headers.update({"Content-Type": "application/json"})
    login(us, email, USER_PW)

    r = us.put(f"{API}/steps/progress", json={
        "step_id": step1_id, "status": "completed",
        "data": _step1_payload("Die Fachsprachenprüfung Medizin ist geplant"),
    })
    assert r.status_code == 200

    progress = us.get(f"{API}/steps/progress").json()
    completed = [p for p in progress if p["status"] == "completed"]
    assert len(completed) == 1, f"expected only Stammdaten completed, got {len(completed)}"


def test_anerkennungsstatus_idempotent(admin_session, steps_by_order):
    """Re-applying same anerkennungsstatus should not double-insert progress_history rows."""
    email = TEST_USERS["petrov"]
    reset_user_progress(admin_session, email)
    step1_id = steps_by_order[1]["id"]

    us = requests.Session(); us.headers.update({"Content-Type": "application/json"})
    login(us, email, USER_PW)
    payload = {"step_id": step1_id, "status": "completed",
               "data": _step1_payload("Ich bin in Deutschland approbiert")}
    hist_before = us.get(f"{API}/steps/history").json()
    before = sum(1 for h in hist_before if h.get("action") == "auto_skipped_by_status")
    us.put(f"{API}/steps/progress", json=payload)
    hist1 = us.get(f"{API}/steps/history").json()
    after1 = sum(1 for h in hist1 if h.get("action") == "auto_skipped_by_status")
    us.put(f"{API}/steps/progress", json=payload)
    hist2 = us.get(f"{API}/steps/history").json()
    after2 = sum(1 for h in hist2 if h.get("action") == "auto_skipped_by_status")
    first_delta = after1 - before
    second_delta = after2 - after1
    assert first_delta == 12, f"first apply should insert 12 auto_skip rows, got {first_delta}"
    assert second_delta == 0, f"re-apply should insert 0 new auto_skip rows, got {second_delta}"


def test_admin_progress_update_triggers_autoskip(admin_session, steps_by_order):
    email = TEST_USERS["tanaka"]
    user_id = reset_user_progress(admin_session, email)
    step1_id = steps_by_order[1]["id"]

    r = admin_session.put(f"{API}/admin/users/{user_id}/progress", json={
        "step_id": step1_id, "status": "completed",
        "data": _step1_payload("Ich bin in Deutschland approbiert"),
    })
    assert r.status_code == 200, r.text
    us = requests.Session(); us.headers.update({"Content-Type": "application/json"})
    login(us, email, USER_PW)
    progress = us.get(f"{API}/steps/progress").json()
    completed = [p for p in progress if p["status"] == "completed"]
    assert len(completed) == 13


# ==========================================================
# Feature 2 — CMS Landing feature boxes
# ==========================================================
REQUIRED_CMS_KEYS = [
    "box1_title", "box1_description",
    "box2_title", "box2_description",
    "box3_title", "box3_description",
]


def test_cms_home_has_feature_box_keys():
    r = requests.get(f"{API}/cms/home")
    assert r.status_code == 200, r.text
    body = r.json()
    content = body.get("content", {})
    translations = body.get("translations", {})
    for k in REQUIRED_CMS_KEYS:
        assert k in content and content[k], f"missing DE {k} in cms/home content"
    en = translations.get("en", {})
    for k in REQUIRED_CMS_KEYS:
        assert k in en and en[k], f"missing EN translation for {k}"


def test_cms_home_update_persists(admin_session):
    current = requests.get(f"{API}/cms/home").json()
    content = dict(current.get("content", {}))
    translations = dict(current.get("translations", {}))
    marker = f"TEST_BOX_{int(time.time())}"
    content["box1_title"] = marker
    r = admin_session.put(f"{API}/cms/home", json={"section": "home", "content": content, "translations": translations})
    assert r.status_code == 200, r.text
    after = requests.get(f"{API}/cms/home").json()
    assert after["content"]["box1_title"] == marker


# ==========================================================
# Feature 3 — Step Template library
# ==========================================================
def test_step_template_crud(admin_session):
    r = admin_session.get(f"{API}/admin/step-templates")
    assert r.status_code == 200
    initial = r.json()
    assert isinstance(initial, list)

    payload = {
        "name": "TEST_tmpl_basic",
        "description": "unit test",
        "config": {"title": "TestStep", "step_type": "form",
                   "fields": [{"name": "foo", "field_type": "text", "label": "Foo"}],
                   "_id": "shouldBeStripped", "order": 999, "is_active": False},
    }
    r = admin_session.post(f"{API}/admin/step-templates", json=payload)
    assert r.status_code == 200, r.text
    tid = r.json()["id"]

    listed = admin_session.get(f"{API}/admin/step-templates").json()
    mine = next(t for t in listed if t["id"] == tid)
    assert mine["name"] == "TEST_tmpl_basic"
    cfg = mine["config"]
    for k in ("_id", "order", "is_active"):
        assert k not in cfg, f"sanitize_template_config should strip {k}"
    assert cfg["title"] == "TestStep"

    r = admin_session.put(f"{API}/admin/step-templates/{tid}", json={
        "name": "TEST_tmpl_renamed",
        "description": "updated",
        "config": {"title": "TestStep2", "step_type": "form"}
    })
    assert r.status_code == 200
    listed = admin_session.get(f"{API}/admin/step-templates").json()
    mine = next(t for t in listed if t["id"] == tid)
    assert mine["name"] == "TEST_tmpl_renamed"
    assert mine["config"]["title"] == "TestStep2"

    r = admin_session.delete(f"{API}/admin/step-templates/{tid}")
    assert r.status_code == 200
    listed = admin_session.get(f"{API}/admin/step-templates").json()
    assert all(t["id"] != tid for t in listed)


def test_template_from_step_and_apply_and_cleanup(admin_session, steps_by_order):
    step1_id = steps_by_order[1]["id"]
    r = admin_session.post(f"{API}/admin/step-templates/from-step/{step1_id}",
                           params={"name": "TEST_tmpl_from_step1", "description": "from step"})
    assert r.status_code == 200, r.text
    tid = r.json()["id"]
    new_step_id = None
    try:
        listed = admin_session.get(f"{API}/admin/step-templates").json()
        mine = next(t for t in listed if t["id"] == tid)
        cfg = mine["config"]
        assert "_id" not in cfg and "order" not in cfg and "is_active" not in cfg
        assert cfg.get("title") and cfg.get("fields")

        target_order = max(steps_by_order.keys()) + 1
        r = admin_session.post(f"{API}/admin/step-templates/{tid}/apply", params={"order": target_order})
        assert r.status_code == 200, r.text
        new_step_id = r.json()["id"]

        all_steps = admin_session.get(f"{API}/admin/steps").json()
        new_step = next((s for s in all_steps if s["id"] == new_step_id), None)
        assert new_step is not None, "applied step not found"
        assert new_step["order"] == target_order

        # verify pending progress entries created for regular users (use kumar fixture)
        us = requests.Session(); us.headers.update({"Content-Type": "application/json"})
        login(us, TEST_USERS["kumar"], USER_PW)
        prog = us.get(f"{API}/steps/progress").json()
        assert any(p["step_id"] == new_step_id for p in prog), "new step should have pending progress for users"
    finally:
        # Always clean up — even if assertions above failed — so we don't leave
        # orphan duplicate steps that pollute everyone's progress data.
        if new_step_id:
            admin_session.put(f"{API}/admin/steps/{new_step_id}", json={"is_active": False})
            admin_session.delete(f"{API}/admin/steps/{new_step_id}")
        admin_session.delete(f"{API}/admin/step-templates/{tid}")
