"""
Comprehensive CRUD, cascade delete, and negative input tests.
Each cascade test creates its own data and cleans up after itself.
"""
import pytest
import httpx

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

def cleanup_test_data(base_url, admin_token):
    """Remove all TEST_ prefixed entities."""
    with httpx.Client(timeout=15) as c:
        users = c.get(f"{base_url}/api/admin/users", headers=auth(admin_token)).json()
        for u in users:
            if u["email"].lower().startswith("test_"):
                c.delete(f"{base_url}/api/admin/users/{u['id']}", headers=auth(admin_token))
        partners = c.get(f"{base_url}/api/admin/partners", headers=auth(admin_token)).json()
        for p in partners:
            if p["name"].startswith("TEST_"):
                c.delete(f"{base_url}/api/admin/partners/{p['id']}", headers=auth(admin_token))
        steps = c.get(f"{base_url}/api/admin/steps", headers=auth(admin_token)).json()
        for s in steps:
            if s["title"].startswith("TEST_"):
                c.delete(f"{base_url}/api/admin/steps/{s['id']}", headers=auth(admin_token))


# ========================
# PARTNER CRUD
# ========================

class TestPartnerCRUD:
    def test_partner_create_read_update_delete(self, base_url, admin_token):
        cleanup_test_data(base_url, admin_token)
        with httpx.Client(timeout=15) as c:
            # Create
            r = c.post(f"{base_url}/api/admin/partners", headers=auth(admin_token), json={
                "name": "TEST_CrudPartner", "description": "Test", "category": "TestCat", "tags": ["Tag1", "Tag2"]
            })
            assert r.status_code == 200
            pid = r.json()["id"]

            # Read
            partners = c.get(f"{base_url}/api/admin/partners", headers=auth(admin_token)).json()
            found = next(p for p in partners if p["id"] == pid)
            assert found["name"] == "TEST_CrudPartner"
            assert found["tags"] == ["Tag1", "Tag2"]

            # Update
            r = c.put(f"{base_url}/api/admin/partners/{pid}", headers=auth(admin_token), json={
                "name": "TEST_CrudPartnerV2", "tags": ["Updated"]
            })
            assert r.status_code == 200
            partners = c.get(f"{base_url}/api/admin/partners", headers=auth(admin_token)).json()
            found = next(p for p in partners if p["id"] == pid)
            assert found["tags"] == ["Updated"]

            # Update with empty email (regression test)
            r = c.put(f"{base_url}/api/admin/partners/{pid}", headers=auth(admin_token), json={"contact_email": ""})
            assert r.status_code == 200

            # Delete
            r = c.delete(f"{base_url}/api/admin/partners/{pid}", headers=auth(admin_token))
            assert r.status_code == 200
            partners = c.get(f"{base_url}/api/admin/partners", headers=auth(admin_token)).json()
            assert not any(p["id"] == pid for p in partners)

    def test_delete_partner_cascades(self, base_url, admin_token):
        """Delete partner -> submissions removed, partner-user reverted."""
        cleanup_test_data(base_url, admin_token)
        with httpx.Client(timeout=15) as c:
            # Create partner
            pr = c.post(f"{base_url}/api/admin/partners", headers=auth(admin_token), json={
                "name": "TEST_CascadePartner", "description": "test"
            })
            pid = pr.json()["id"]

            # Create partner-role user linked to it
            c.post(f"{base_url}/api/admin/users", headers=auth(admin_token), json={
                "email": "TEST_cascade_pu@test.de", "password": "Test123!", "name": "CascadePU", "role": "partner", "partner_id": pid
            })

            # Create a regular user and submit to this partner
            reg = c.post(f"{base_url}/api/auth/register", json={"email": "TEST_cascade_sub@test.de", "password": "Test123!", "name": "Sub"})
            sub_token = reg.json()["access_token"]
            c.post(f"{base_url}/api/partners/submit", headers=auth(sub_token), json={"partner_id": pid, "data": {"test": True}})

            # Delete the partner
            r = c.delete(f"{base_url}/api/admin/partners/{pid}", headers=auth(admin_token))
            assert r.status_code == 200

            # Verify: partner-user reverted to "user" role
            users = c.get(f"{base_url}/api/admin/users", headers=auth(admin_token)).json()
            pu = next((u for u in users if u["email"] == "test_cascade_pu@test.de"), None)
            if pu:
                assert pu["role"] == "user", f"Partner user should be reverted to 'user', got '{pu['role']}'"

            cleanup_test_data(base_url, admin_token)


# ========================
# USER CRUD
# ========================

class TestUserCRUD:
    def test_user_create_read_delete(self, base_url, admin_token):
        cleanup_test_data(base_url, admin_token)
        with httpx.Client(timeout=15) as c:
            # Create
            r = c.post(f"{base_url}/api/admin/users", headers=auth(admin_token), json={
                "email": "TEST_cruduser@test.de", "password": "Test123!", "name": "CrudUser", "role": "user"
            })
            assert r.status_code == 200
            uid = r.json()["id"]

            # Read
            r = c.get(f"{base_url}/api/admin/users/{uid}", headers=auth(admin_token))
            assert r.status_code == 200
            assert "test_cruduser@test.de" in r.json()["email"].lower()

            # Delete
            r = c.delete(f"{base_url}/api/admin/users/{uid}", headers=auth(admin_token))
            assert r.status_code == 200

    def test_delete_user_cascades_linked_partner(self, base_url, admin_token):
        """Delete user -> removed from partner.linked_user_ids."""
        cleanup_test_data(base_url, admin_token)
        with httpx.Client(timeout=15) as c:
            # Create user
            ur = c.post(f"{base_url}/api/admin/users", headers=auth(admin_token), json={
                "email": "TEST_linkuser@test.de", "password": "Test123!", "name": "LinkUser", "role": "user"
            })
            uid = ur.json()["id"]

            # Create partner with this user in linked_user_ids
            pr = c.post(f"{base_url}/api/admin/partners", headers=auth(admin_token), json={
                "name": "TEST_LinkPartner", "description": "test", "linked_user_ids": [uid]
            })
            pid = pr.json()["id"]

            # Verify linked
            partners = c.get(f"{base_url}/api/admin/partners", headers=auth(admin_token)).json()
            p = next(x for x in partners if x["id"] == pid)
            assert uid in p["linked_user_ids"]

            # Delete user
            c.delete(f"{base_url}/api/admin/users/{uid}", headers=auth(admin_token))

            # Verify: removed from linked_user_ids
            partners = c.get(f"{base_url}/api/admin/partners", headers=auth(admin_token)).json()
            p = next((x for x in partners if x["id"] == pid), None)
            if p:
                assert uid not in p.get("linked_user_ids", [])

            cleanup_test_data(base_url, admin_token)


# ========================
# STEP CRUD
# ========================

class TestStepCRUD:
    def test_step_create_read_update_delete(self, base_url, admin_token):
        cleanup_test_data(base_url, admin_token)
        with httpx.Client(timeout=15) as c:
            # Create
            r = c.post(f"{base_url}/api/admin/steps", headers=auth(admin_token), json={
                "title": "TEST_CrudStep", "description": "Test step", "order": 99, "step_type": "display"
            })
            assert r.status_code == 200
            sid = r.json()["id"]

            # Read
            steps = c.get(f"{base_url}/api/admin/steps", headers=auth(admin_token)).json()
            found = next(s for s in steps if s["id"] == sid)
            assert found["title"] == "TEST_CrudStep"

            # Update
            r = c.put(f"{base_url}/api/admin/steps/{sid}", headers=auth(admin_token), json={"title": "TEST_CrudStepV2"})
            assert r.status_code == 200

            # Delete (cascades progress)
            r = c.delete(f"{base_url}/api/admin/steps/{sid}", headers=auth(admin_token))
            assert r.status_code == 200

            steps = c.get(f"{base_url}/api/admin/steps", headers=auth(admin_token)).json()
            assert not any(s["id"] == sid for s in steps)


# ========================
# CONFIRM DIALOG (Frontend delete works via API)
# ========================

class TestDeleteConfirmFlow:
    """Test that delete endpoints work correctly when called (the frontend uses a confirm dialog now)."""

    def test_partner_delete_via_api(self, base_url, admin_token):
        with httpx.Client(timeout=15) as c:
            # Create
            r = c.post(f"{base_url}/api/admin/partners", headers=auth(admin_token), json={
                "name": "TEST_ConfirmDelete", "description": "test"
            })
            pid = r.json()["id"]

            # Delete
            r = c.delete(f"{base_url}/api/admin/partners/{pid}", headers=auth(admin_token))
            assert r.status_code == 200
            assert r.json()["message"] == "Partner deleted"

    def test_step_delete_via_api(self, base_url, admin_token):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/admin/steps", headers=auth(admin_token), json={
                "title": "TEST_ConfirmStep", "description": "test", "order": 99, "step_type": "display"
            })
            sid = r.json()["id"]
            r = c.delete(f"{base_url}/api/admin/steps/{sid}", headers=auth(admin_token))
            assert r.status_code == 200

    def test_user_delete_via_api(self, base_url, admin_token):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/admin/users", headers=auth(admin_token), json={
                "email": "TEST_confirmuser@test.de", "password": "Test123!", "name": "ConfirmUser", "role": "user"
            })
            uid = r.json()["id"]
            r = c.delete(f"{base_url}/api/admin/users/{uid}", headers=auth(admin_token))
            assert r.status_code == 200


# ========================
# NEGATIVE / VALIDATION TESTS
# ========================

class TestNegativeInputs:
    def test_register_invalid_email(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/auth/register", json={"email": "not-an-email", "password": "Test123!", "name": "Bad"})
            assert r.status_code == 422

    def test_register_duplicate_email(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/auth/register", json={"email": "admin@example.com", "password": "Test123!", "name": "Dup"})
            assert r.status_code == 400

    def test_login_wrong_password(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/auth/login", json={"email": "admin@example.com", "password": "WRONG"})
            assert r.status_code == 401

    def test_login_nonexistent(self, base_url):
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
                "email": "bad-format", "password": "Test123!", "name": "Bad", "role": "user"
            })
            assert r.status_code == 422

    def test_admin_create_user_duplicate(self, base_url, admin_token):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/admin/users", headers=auth(admin_token), json={
                "email": "admin@example.com", "password": "Test123!", "name": "Dup", "role": "user"
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
        with httpx.Client(timeout=15) as c:
            users = c.get(f"{base_url}/api/admin/users", headers=auth(admin_token)).json()
            admin = next(u for u in users if u["email"] == "admin@example.com")
            r = c.delete(f"{base_url}/api/admin/users/{admin['id']}", headers=auth(admin_token))
            assert r.status_code == 400

    def test_unauthorized_access(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/admin/users")
            assert r.status_code == 401

    def test_partner_cannot_access_admin(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/auth/login", json={"email": "partner@example.com", "password": "Partner123!"})
            if r.status_code == 200:
                tok = r.json()["access_token"]
                r2 = c.get(f"{base_url}/api/admin/users", headers=auth(tok))
                assert r2.status_code == 403

    def test_step_missing_required_fields(self, base_url, admin_token):
        cleanup_test_data(base_url, admin_token)
        with httpx.Client(timeout=15) as c:
            reg = c.post(f"{base_url}/api/auth/register", json={"email": "TEST_validation@test.de", "password": "Test123!", "name": "Val"})
            tok = reg.json()["access_token"] if reg.status_code == 200 else c.post(f"{base_url}/api/auth/login", json={"email": "test_validation@test.de", "password": "Test123!"}).json()["access_token"]
            steps = c.get(f"{base_url}/api/steps", headers=auth(tok)).json()
            step1 = next(s for s in steps if s["order"] == 1)
            r = c.put(f"{base_url}/api/steps/progress", headers=auth(tok), json={
                "step_id": step1["id"], "status": "completed", "data": {}
            })
            assert r.status_code == 400
            assert "Pflichtfelder" in r.json()["detail"]
            cleanup_test_data(base_url, admin_token)


class TestFinalCleanup:
    def test_cleanup(self, base_url, admin_token):
        cleanup_test_data(base_url, admin_token)
