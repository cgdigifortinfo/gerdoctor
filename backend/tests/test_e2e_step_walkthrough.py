"""
E2E Test: A user walks through all 12 steps.
After each step, verify the result from user, admin, and partner perspective.
"""
import pytest
import httpx
import asyncio

API_URL = None
ADMIN_TOKEN = None
ADMIN_EMAIL = "admin@example.com"
ADMIN_PW = "Admin123!"
TEST_USER_EMAIL = "TEST_e2e_fullwalk@gerdoctor.de"
TEST_USER_PW = "TestWalk123!"
TEST_USER_NAME = "Dr. E2E Walker"

@pytest.fixture(scope="module")
def base_url():
    import subprocess
    result = subprocess.run(["grep", "REACT_APP_BACKEND_URL", "/app/frontend/.env"], capture_output=True, text=True)
    url = result.stdout.strip().split("=", 1)[1]
    return url

@pytest.fixture(scope="module")
def admin_token(base_url):
    with httpx.Client(timeout=15) as c:
        r = c.post(f"{base_url}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW})
        assert r.status_code == 200
        return r.json()["access_token"]

@pytest.fixture(scope="module")
def steps_list(base_url, admin_token):
    with httpx.Client(timeout=15) as c:
        r = c.get(f"{base_url}/api/admin/steps", headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        steps = sorted(r.json(), key=lambda s: s["order"])
        return steps

@pytest.fixture(scope="module")
def partners_by_tag(base_url):
    with httpx.Client(timeout=15) as c:
        result = {}
        for tag in ["Antragstellung", "Gleichwertigkeitspruefung", "Kenntnisprüfung", "Weiterbildung", "Praxis"]:
            r = c.get(f"{base_url}/api/partners", params={"tag": tag})
            assert r.status_code == 200
            result[tag] = r.json()
        return result

@pytest.fixture(scope="module")
def user_token(base_url):
    with httpx.Client(timeout=15) as c:
        # Register test user
        r = c.post(f"{base_url}/api/auth/register", json={"email": TEST_USER_EMAIL, "password": TEST_USER_PW, "name": TEST_USER_NAME})
        if r.status_code == 400:
            # Already exists, login
            r = c.post(f"{base_url}/api/auth/login", json={"email": TEST_USER_EMAIL, "password": TEST_USER_PW})
        assert r.status_code == 200
        return r.json()["access_token"]

def auth(token):
    return {"Authorization": f"Bearer {token}"}

def complete_step(base_url, user_token, step_id, data):
    with httpx.Client(timeout=15) as c:
        r = c.put(f"{base_url}/api/steps/progress", headers=auth(user_token),
                   json={"step_id": step_id, "status": "completed", "data": data})
        return r

def get_user_progress(base_url, user_token):
    with httpx.Client(timeout=15) as c:
        r = c.get(f"{base_url}/api/steps/progress", headers=auth(user_token))
        assert r.status_code == 200
        return {p["step_id"]: p for p in r.json()}

def admin_check_user(base_url, admin_token, user_email):
    with httpx.Client(timeout=15) as c:
        r = c.get(f"{base_url}/api/admin/users", headers=auth(admin_token))
        assert r.status_code == 200
        users = r.json()
        return next((u for u in users if u["email"] == user_email.lower()), None)


class TestFullStepWalkthrough:
    """User walks through all 12 steps sequentially."""

    def test_step_01_persoenliche_daten(self, base_url, user_token, admin_token, steps_list):
        step = steps_list[0]
        assert step["title"] == "Persönliche Daten"
        assert step["step_type"] == "form"

        data = {"name": "Walker", "first_name": "E2E", "phone": "+49 170 1234567",
                "address": "Teststr. 1, 10115 Berlin", "field_of_study": "Chirurgie"}
        r = complete_step(base_url, user_token, step["id"], data)
        assert r.status_code == 200

        # Verify progress
        progress = get_user_progress(base_url, user_token)
        assert progress[step["id"]]["status"] == "completed"
        assert progress[step["id"]]["data"]["name"] == "Walker"

        # Admin sees correct completion
        admin_user = admin_check_user(base_url, admin_token, TEST_USER_EMAIL)
        assert admin_user is not None
        assert admin_user["completion_pct"] == 0  # No duration-steps completed yet

    def test_step_02_antragstellung(self, base_url, user_token, admin_token, steps_list, partners_by_tag):
        step = steps_list[1]
        assert step["step_type"] == "partner_selection"
        assert step["filter_tag"] == "Antragstellung"

        partners = partners_by_tag["Antragstellung"]
        assert len(partners) > 0
        chosen = partners[0]

        # Submit to partner
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/partners/submit", headers=auth(user_token),
                       json={"partner_id": chosen["id"], "data": {"selected_partner_id": chosen["id"], "selected_partner_name": chosen["name"]}})
            assert r.status_code == 200

        # Complete the step
        r = complete_step(base_url, user_token, step["id"],
                          {"selected_partner_id": chosen["id"], "selected_partner_name": chosen["name"]})
        assert r.status_code == 200

        progress = get_user_progress(base_url, user_token)
        assert progress[step["id"]]["status"] == "completed"
        assert progress[step["id"]]["data"]["selected_partner_name"] == chosen["name"]

    def test_step_03_uebersicht_antragstellung(self, base_url, user_token, admin_token, steps_list):
        step = steps_list[2]
        assert step["step_type"] == "milestone"
        assert step["duration_value"] == 4

        r = complete_step(base_url, user_token, step["id"], {})
        assert r.status_code == 200

        # First duration-step completed -> 33%
        admin_user = admin_check_user(base_url, admin_token, TEST_USER_EMAIL)
        assert admin_user["completion_pct"] == 33

    def test_step_04_famed(self, base_url, user_token, steps_list):
        step = steps_list[3]
        assert step["step_type"] == "display"
        assert step["title"] == "FaMed"

        r = complete_step(base_url, user_token, step["id"], {})
        assert r.status_code == 200

        progress = get_user_progress(base_url, user_token)
        assert progress[step["id"]]["status"] == "completed"

    def test_step_05_gleichwertigkeitspruefung(self, base_url, user_token, steps_list, partners_by_tag):
        step = steps_list[4]
        assert step["step_type"] == "partner_selection"
        assert step["filter_tag"] == "Gleichwertigkeitspruefung"

        partners = partners_by_tag["Gleichwertigkeitspruefung"]
        assert len(partners) > 0
        chosen = partners[0]

        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/partners/submit", headers=auth(user_token),
                       json={"partner_id": chosen["id"], "data": {"selected_partner_id": chosen["id"], "selected_partner_name": chosen["name"]}})
            assert r.status_code == 200

        r = complete_step(base_url, user_token, step["id"],
                          {"selected_partner_id": chosen["id"], "selected_partner_name": chosen["name"]})
        assert r.status_code == 200

    def test_step_06_uebersicht_gleichwertigkeit(self, base_url, user_token, admin_token, steps_list):
        step = steps_list[5]
        assert step["step_type"] == "milestone"
        assert step["duration_value"] == 3

        r = complete_step(base_url, user_token, step["id"], {})
        assert r.status_code == 200

        # 2 of 3 duration-steps -> 67%
        admin_user = admin_check_user(base_url, admin_token, TEST_USER_EMAIL)
        assert admin_user["completion_pct"] == 67

    def test_step_07_service_kenntnisspruefung(self, base_url, user_token, steps_list, partners_by_tag):
        step = steps_list[6]
        assert step["step_type"] == "partner_selection"

        partners = partners_by_tag["Kenntnisprüfung"]
        assert len(partners) > 0
        chosen = partners[0]

        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/partners/submit", headers=auth(user_token),
                       json={"partner_id": chosen["id"], "data": {"selected_partner_id": chosen["id"], "selected_partner_name": chosen["name"]}})
            assert r.status_code == 200

        r = complete_step(base_url, user_token, step["id"],
                          {"selected_partner_id": chosen["id"], "selected_partner_name": chosen["name"]})
        assert r.status_code == 200

    def test_step_08_meilenstein_kenntnisspruefung(self, base_url, user_token, admin_token, steps_list):
        step = steps_list[7]
        assert step["step_type"] == "milestone"
        assert step["duration_value"] == 3

        r = complete_step(base_url, user_token, step["id"], {})
        assert r.status_code == 200

        # All 3 duration-steps completed -> 100%
        admin_user = admin_check_user(base_url, admin_token, TEST_USER_EMAIL)
        assert admin_user["completion_pct"] == 100

    def test_step_09_service_weiterbildung(self, base_url, user_token, steps_list, partners_by_tag):
        step = steps_list[8]
        assert step["step_type"] == "partner_selection"

        partners = partners_by_tag["Weiterbildung"]
        assert len(partners) > 0
        chosen = partners[0]

        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/partners/submit", headers=auth(user_token),
                       json={"partner_id": chosen["id"], "data": {"selected_partner_id": chosen["id"], "selected_partner_name": chosen["name"]}})
            assert r.status_code == 200

        r = complete_step(base_url, user_token, step["id"],
                          {"selected_partner_id": chosen["id"], "selected_partner_name": chosen["name"]})
        assert r.status_code == 200

    def test_step_10_meilenstein_job(self, base_url, user_token, steps_list):
        step = steps_list[9]
        r = complete_step(base_url, user_token, step["id"], {})
        assert r.status_code == 200

    def test_step_11_jobangebote(self, base_url, user_token, steps_list, partners_by_tag):
        step = steps_list[10]
        assert step["step_type"] == "partner_multiselection"

        praxis = partners_by_tag["Praxis"]
        assert len(praxis) >= 2
        chosen_ids = [p["id"] for p in praxis[:2]]

        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/partners/submit-multi", headers=auth(user_token),
                       json={"partner_ids": chosen_ids, "data": {}})
            assert r.status_code == 200

        data = {
            "selected_partner_ids": chosen_ids,
            "selected_partner_names": ", ".join([p["name"] for p in praxis[:2]])
        }
        r = complete_step(base_url, user_token, step["id"], data)
        assert r.status_code == 200

    def test_step_12_beworben(self, base_url, user_token, admin_token, steps_list):
        step = steps_list[11]
        r = complete_step(base_url, user_token, step["id"], {})
        assert r.status_code == 200

        # ALL steps completed
        progress = get_user_progress(base_url, user_token)
        all_completed = all(p["status"] == "completed" for p in progress.values())
        assert all_completed, f"Not all steps completed: {[(sid, p['status']) for sid, p in progress.items() if p['status'] != 'completed']}"

        admin_user = admin_check_user(base_url, admin_token, TEST_USER_EMAIL)
        assert admin_user["completion_pct"] == 100

    def test_partner_sees_user(self, base_url, steps_list, partners_by_tag):
        """Partner who was chosen in step 2 should see the test user."""
        chosen_partner = partners_by_tag["Antragstellung"][0]

        # Find partner user for this partner
        with httpx.Client(timeout=15) as c:
            admin_r = c.post(f"{base_url}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW})
            admin_tok = admin_r.json()["access_token"]
            partners = c.get(f"{base_url}/api/admin/partners", headers=auth(admin_tok)).json()
            partner = next((p for p in partners if p["id"] == chosen_partner["id"]), None)
            assert partner is not None

            if partner.get("user_id"):
                # Find partner user email
                users = c.get(f"{base_url}/api/admin/users", headers=auth(admin_tok)).json()
                partner_user = next((u for u in users if u["id"] == partner["user_id"]), None)
                if partner_user:
                    # Login as partner
                    pr = c.post(f"{base_url}/api/auth/login", json={"email": partner_user["email"], "password": "Partner123!"})
                    if pr.status_code == 200:
                        ptok = pr.json()["access_token"]
                        subs = c.get(f"{base_url}/api/partner/submissions", headers=auth(ptok)).json()
                        test_user_sub = [s for s in subs if s.get("user_email", "").lower() == TEST_USER_EMAIL.lower()]
                        assert len(test_user_sub) > 0, f"Partner does not see test user. Submissions: {[s.get('user_email') for s in subs]}"

    def test_admin_user_detail(self, base_url, admin_token):
        """Admin can view full detail of the test user."""
        with httpx.Client(timeout=15) as c:
            users = c.get(f"{base_url}/api/admin/users", headers=auth(admin_token)).json()
            test_user = next((u for u in users if u["email"] == TEST_USER_EMAIL.lower()), None)
            assert test_user is not None

            detail = c.get(f"{base_url}/api/admin/users/{test_user['id']}", headers=auth(admin_token)).json()
            assert detail["completion_pct"] == 100
            assert len(detail["progress"]) == 12
            assert all(p["status"] == "completed" for p in detail["progress"])


class TestCleanup:
    def test_cleanup(self, base_url, admin_token):
        with httpx.Client(timeout=15) as c:
            users = c.get(f"{base_url}/api/admin/users", headers=auth(admin_token)).json()
            test_user = next((u for u in users if u["email"] == TEST_USER_EMAIL.lower()), None)
            if test_user:
                r = c.delete(f"{base_url}/api/admin/users/{test_user['id']}", headers=auth(admin_token))
                assert r.status_code == 200
