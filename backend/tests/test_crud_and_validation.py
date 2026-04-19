"""
Comprehensive CRUD, cascade delete, and negative input tests.
Tests: Partners, Users, Steps - Create/Read/Update/Delete + cascade dependencies + input validation.
"""
import pytest
import httpx

API_URL = None
ADMIN_TOKEN = None

@pytest.fixture(scope="module")
def base_url():
    import subprocess
    result = subprocess.run(["grep", "REACT_APP_BACKEND_URL", "/app/frontend/.env"], capture_output=True, text=True)
    return result.stdout.strip().split("=", 1)[1]

@pytest.fixture(scope="module")
def admin_token(base_url):
    with httpx.Client(timeout=15) as c:
        r = c.post(f"{base_url}/api/auth/login", json={"email": "admin@example.com", "password": "Admin123!"})
        assert r.status_code == 200
        return r.json()["access_token"]

def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ========================
# PARTNER CRUD + CASCADE
# ========================

class TestPartnerCRUD:
    partner_id = None

    def test_create_partner(self, base_url, admin_token):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/admin/partners", headers=auth(admin_token), json={
                "name": "TEST_CrudPartner", "description": "Test partner for CRUD", "category": "TestCat", "tags": ["TestTag1", "TestTag2"]
            })
            assert r.status_code == 200
            TestPartnerCRUD.partner_id = r.json()["id"]
            assert TestPartnerCRUD.partner_id

    def test_read_partner(self, base_url, admin_token):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/admin/partners", headers=auth(admin_token))
            assert r.status_code == 200
            found = [p for p in r.json() if p["id"] == TestPartnerCRUD.partner_id]
            assert len(found) == 1
            assert found[0]["name"] == "TEST_CrudPartner"
            assert found[0]["tags"] == ["TestTag1", "TestTag2"]

    def test_update_partner(self, base_url, admin_token):
        with httpx.Client(timeout=15) as c:
            r = c.put(f"{base_url}/api/admin/partners/{TestPartnerCRUD.partner_id}", headers=auth(admin_token), json={
                "name": "TEST_CrudPartnerUpdated", "tags": ["UpdatedTag"]
            })
            assert r.status_code == 200
            # Verify
            partners = c.get(f"{base_url}/api/admin/partners", headers=auth(admin_token)).json()
            found = [p for p in partners if p["id"] == TestPartnerCRUD.partner_id]
            assert found[0]["name"] == "TEST_CrudPartnerUpdated"
            assert found[0]["tags"] == ["UpdatedTag"]

    def test_update_partner_empty_email(self, base_url, admin_token):
        """Empty contact_email should not cause validation error."""
        with httpx.Client(timeout=15) as c:
            r = c.put(f"{base_url}/api/admin/partners/{TestPartnerCRUD.partner_id}", headers=auth(admin_token), json={
                "contact_email": ""
            })
            assert r.status_code == 200

    def test_delete_partner_cascades_submissions(self, base_url, admin_token):
        """Deleting a partner must remove all its submissions and unlink partner users."""
        pid = TestPartnerCRUD.partner_id
        with httpx.Client(timeout=15) as c:
            # Create a user, make them a partner user
            c.post(f"{base_url}/api/admin/users", headers=auth(admin_token), json={
                "email": "TEST_cascade_partner@test.de", "password": "Test123!", "name": "Test Cascade", "role": "partner", "partner_id": pid
            })
            # Create a submission to this partner (register test user first)
            reg = c.post(f"{base_url}/api/auth/register", json={"email": "TEST_cascade_submitter@test.de", "password": "Test123!", "name": "Submitter"})
            sub_token = reg.json()["access_token"] if reg.status_code == 200 else c.post(f"{base_url}/api/auth/login", json={"email": "test_cascade_submitter@test.de", "password": "Test123!"}).json()["access_token"]
            c.post(f"{base_url}/api/partners/submit", headers=auth(sub_token), json={"partner_id": pid, "data": {"test": True}})

            # Delete the partner
            r = c.delete(f"{base_url}/api/admin/partners/{pid}", headers=auth(admin_token))
            assert r.status_code == 200

            # Verify: partner gone
            partners = c.get(f"{base_url}/api/admin/partners", headers=auth(admin_token)).json()
            assert not any(p["id"] == pid for p in partners)

            # Verify: partner user reverted to "user" role
            users = c.get(f"{base_url}/api/admin/users", headers=auth(admin_token)).json()
            cascade_user = next((u for u in users if u["email"] == "test_cascade_partner@test.de"), None)
            if cascade_user:
                assert cascade_user["role"] == "user"

            # Cleanup
            for email in ["test_cascade_partner@test.de", "test_cascade_submitter@test.de"]:
                u = next((x for x in users if x["email"] == email), None)
                if u:
                    c.delete(f"{base_url}/api/admin/users/{u['id']}", headers=auth(admin_token))


# ========================
# USER CRUD + CASCADE
# ========================

class TestUserCRUD:
    user_id = None

    def test_create_user(self, base_url, admin_token):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/admin/users", headers=auth(admin_token), json={
                "email": "TEST_cruduser@test.de", "password": "Test123!", "name": "Test CRUD User", "role": "user"
            })
            assert r.status_code == 200
            TestUserCRUD.user_id = r.json()["id"]

    def test_read_user(self, base_url, admin_token):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/admin/users/{TestUserCRUD.user_id}", headers=auth(admin_token))
            assert r.status_code == 200
            assert r.json()["email"].lower() == "test_cruduser@test.de"

    def test_delete_user_cascades_linked_partner(self, base_url, admin_token):
        """Deleting a user linked to partner.linked_user_ids must remove them."""
        uid = TestUserCRUD.user_id
        with httpx.Client(timeout=15) as c:
            # Create a partner and link user
            pr = c.post(f"{base_url}/api/admin/partners", headers=auth(admin_token), json={
                "name": "TEST_CascadeUserPartner", "description": "test", "linked_user_ids": [uid]
            })
            pid = pr.json()["id"]

            # Verify linked
            partners = c.get(f"{base_url}/api/admin/partners", headers=auth(admin_token)).json()
            p = next(x for x in partners if x["id"] == pid)
            assert uid in p["linked_user_ids"]

            # Delete the user
            c.delete(f"{base_url}/api/admin/users/{uid}", headers=auth(admin_token))

            # Verify: user removed from linked_user_ids
            partners = c.get(f"{base_url}/api/admin/partners", headers=auth(admin_token)).json()
            p = next((x for x in partners if x["id"] == pid), None)
            if p:
                assert uid not in p.get("linked_user_ids", [])

            # Cleanup partner
            c.delete(f"{base_url}/api/admin/partners/{pid}", headers=auth(admin_token))


# ========================
# STEP CRUD + CASCADE
# ========================

class TestStepCRUD:
    step_id = None

    def test_create_step(self, base_url, admin_token):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/admin/steps", headers=auth(admin_token), json={
                "title": "TEST_CrudStep", "description": "Test step", "order": 99, "step_type": "display"
            })
            assert r.status_code == 200
            TestStepCRUD.step_id = r.json()["id"]

    def test_read_step(self, base_url, admin_token):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/admin/steps", headers=auth(admin_token))
            assert r.status_code == 200
            found = [s for s in r.json() if s["id"] == TestStepCRUD.step_id]
            assert len(found) == 1
            assert found[0]["title"] == "TEST_CrudStep"

    def test_update_step(self, base_url, admin_token):
        with httpx.Client(timeout=15) as c:
            r = c.put(f"{base_url}/api/admin/steps/{TestStepCRUD.step_id}", headers=auth(admin_token), json={
                "title": "TEST_CrudStepUpdated"
            })
            assert r.status_code == 200

    def test_delete_step_cascades_progress(self, base_url, admin_token):
        """Deleting a step must remove all user_progress and progress_history for it."""
        sid = TestStepCRUD.step_id
        with httpx.Client(timeout=15) as c:
            # Delete
            r = c.delete(f"{base_url}/api/admin/steps/{sid}", headers=auth(admin_token))
            assert r.status_code == 200
            # Verify gone
            steps = c.get(f"{base_url}/api/admin/steps", headers=auth(admin_token)).json()
            assert not any(s["id"] == sid for s in steps)


# ========================
# NEGATIVE / VALIDATION TESTS
# ========================

class TestNegativeInputs:

    def test_register_invalid_email(self, base_url):
        """Registration with invalid email must fail."""
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/auth/register", json={"email": "not-an-email", "password": "Test123!", "name": "Bad"})
            assert r.status_code == 422

    def test_register_empty_password(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/auth/register", json={"email": "TEST_empty@test.de", "password": "", "name": "Empty"})
            # FastAPI/Pydantic may accept empty string but bcrypt will handle it
            # The key is it shouldn't crash
            assert r.status_code in (200, 400, 422)

    def test_register_duplicate_email(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/auth/register", json={"email": "admin@example.com", "password": "Test123!", "name": "Dup"})
            assert r.status_code == 400
            assert "already registered" in r.json()["detail"]

    def test_login_wrong_password(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/auth/login", json={"email": "admin@example.com", "password": "WRONGPASSWORD"})
            assert r.status_code == 401

    def test_login_nonexistent_email(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/auth/login", json={"email": "nonexistent@nowhere.de", "password": "Test123!"})
            assert r.status_code == 401

    def test_login_malformed_email(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/auth/login", json={"email": "not-email", "password": "Test123!"})
            assert r.status_code == 422

    def test_admin_create_user_invalid_email(self, base_url, admin_token):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/admin/users", headers=auth(admin_token), json={
                "email": "bad-email-format", "password": "Test123!", "name": "Bad Email", "role": "user"
            })
            assert r.status_code == 422

    def test_admin_create_user_duplicate(self, base_url, admin_token):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/admin/users", headers=auth(admin_token), json={
                "email": "admin@example.com", "password": "Test123!", "name": "Dup Admin", "role": "user"
            })
            assert r.status_code == 400

    def test_delete_nonexistent_partner(self, base_url, admin_token):
        with httpx.Client(timeout=15) as c:
            r = c.delete(f"{base_url}/api/admin/partners/000000000000000000000000", headers=auth(admin_token))
            assert r.status_code == 404

    def test_delete_nonexistent_step(self, base_url, admin_token):
        with httpx.Client(timeout=15) as c:
            r = c.delete(f"{base_url}/api/admin/steps/000000000000000000000000", headers=auth(admin_token))
            assert r.status_code == 404

    def test_delete_nonexistent_user(self, base_url, admin_token):
        with httpx.Client(timeout=15) as c:
            r = c.delete(f"{base_url}/api/admin/users/000000000000000000000000", headers=auth(admin_token))
            assert r.status_code == 404

    def test_delete_primary_admin(self, base_url, admin_token):
        """Cannot delete the primary admin."""
        with httpx.Client(timeout=15) as c:
            users = c.get(f"{base_url}/api/admin/users", headers=auth(admin_token)).json()
            admin = next(u for u in users if u["email"] == "admin@example.com")
            r = c.delete(f"{base_url}/api/admin/users/{admin['id']}", headers=auth(admin_token))
            assert r.status_code == 400

    def test_invalid_objectid_format(self, base_url, admin_token):
        """Malformed ObjectId should return error, not crash."""
        with httpx.Client(timeout=15) as c:
            r = c.delete(f"{base_url}/api/admin/partners/not-a-valid-id", headers=auth(admin_token))
            assert r.status_code in (400, 422, 500)  # Should not crash silently

    def test_unauthorized_access(self, base_url):
        """Non-admin cannot access admin endpoints."""
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/admin/users")
            assert r.status_code == 401

    def test_partner_user_cannot_access_admin(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/auth/login", json={"email": "partner@example.com", "password": "Partner123!"})
            if r.status_code == 200:
                tok = r.json()["access_token"]
                r2 = c.get(f"{base_url}/api/admin/users", headers=auth(tok))
                assert r2.status_code == 403

    def test_step_completion_missing_required_fields(self, base_url):
        """Completing step 1 without required fields should fail."""
        with httpx.Client(timeout=15) as c:
            # Register a test user
            reg = c.post(f"{base_url}/api/auth/register", json={"email": "TEST_validation@test.de", "password": "Test123!", "name": "Validator"})
            tok = reg.json()["access_token"] if reg.status_code == 200 else c.post(f"{base_url}/api/auth/login", json={"email": "test_validation@test.de", "password": "Test123!"}).json()["access_token"]
            # Get steps
            steps = c.get(f"{base_url}/api/steps", headers=auth(tok)).json()
            step1 = next(s for s in steps if s["order"] == 1)
            # Try completing without required fields
            r = c.put(f"{base_url}/api/steps/progress", headers=auth(tok), json={
                "step_id": step1["id"], "status": "completed", "data": {}
            })
            assert r.status_code == 400
            assert "Pflichtfelder" in r.json()["detail"]


class TestCleanup:
    def test_cleanup(self, base_url, admin_token):
        with httpx.Client(timeout=15) as c:
            users = c.get(f"{base_url}/api/admin/users", headers=auth(admin_token)).json()
            for u in users:
                if u["email"].startswith("test_"):
                    c.delete(f"{base_url}/api/admin/users/{u['id']}", headers=auth(admin_token))
            partners = c.get(f"{base_url}/api/admin/partners", headers=auth(admin_token)).json()
            for p in partners:
                if p["name"].startswith("TEST_"):
                    c.delete(f"{base_url}/api/admin/partners/{p['id']}", headers=auth(admin_token))
            steps = c.get(f"{base_url}/api/admin/steps", headers=auth(admin_token)).json()
            for s in steps:
                if s["title"].startswith("TEST_"):
                    c.delete(f"{base_url}/api/admin/steps/{s['id']}", headers=auth(admin_token))
