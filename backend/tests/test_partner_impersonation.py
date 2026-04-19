"""
Test: Admin impersonation of partner users.
Verifies that impersonating a partner user gives access to the Partner Dashboard.
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


class TestPartnerImpersonation:

    def test_impersonate_partner_user(self, base_url, admin_token):
        """Admin can impersonate a partner user and get a valid token."""
        with httpx.Client(timeout=15) as c:
            users = c.get(f"{base_url}/api/admin/users", headers=auth(admin_token)).json()
            partner_user = next(u for u in users if u["email"] == "partner@example.com")

            r = c.post(f"{base_url}/api/admin/impersonate/{partner_user['id']}", headers=auth(admin_token))
            assert r.status_code == 200
            imp_token = r.json()["access_token"]
            assert imp_token

    def test_impersonated_partner_can_get_submissions(self, base_url, admin_token):
        """Impersonated partner user can access /partner/submissions."""
        with httpx.Client(timeout=15) as c:
            users = c.get(f"{base_url}/api/admin/users", headers=auth(admin_token)).json()
            partner_user = next(u for u in users if u["email"] == "partner@example.com")

            imp_token = c.post(f"{base_url}/api/admin/impersonate/{partner_user['id']}", headers=auth(admin_token)).json()["access_token"]

            r = c.get(f"{base_url}/api/partner/submissions", headers=auth(imp_token))
            assert r.status_code == 200
            subs = r.json()
            assert isinstance(subs, list)
            assert len(subs) > 0

    def test_impersonated_partner_can_get_profile(self, base_url, admin_token):
        """Impersonated partner user can access /partner/profile."""
        with httpx.Client(timeout=15) as c:
            users = c.get(f"{base_url}/api/admin/users", headers=auth(admin_token)).json()
            partner_user = next(u for u in users if u["email"] == "partner@example.com")

            imp_token = c.post(f"{base_url}/api/admin/impersonate/{partner_user['id']}", headers=auth(admin_token)).json()["access_token"]

            r = c.get(f"{base_url}/api/partner/profile", headers=auth(imp_token))
            assert r.status_code == 200
            profile = r.json()
            assert profile["email"] == "partner@example.com"
            assert profile["partner_name"] is not None

    def test_impersonated_partner_can_get_other_users(self, base_url, admin_token):
        """Impersonated partner user can access /partner/other-users."""
        with httpx.Client(timeout=15) as c:
            users = c.get(f"{base_url}/api/admin/users", headers=auth(admin_token)).json()
            partner_user = next(u for u in users if u["email"] == "partner@example.com")

            imp_token = c.post(f"{base_url}/api/admin/impersonate/{partner_user['id']}", headers=auth(admin_token)).json()["access_token"]

            r = c.get(f"{base_url}/api/partner/other-users", headers=auth(imp_token))
            assert r.status_code == 200
            assert isinstance(r.json(), list)

    def test_impersonated_partner_can_view_user_detail(self, base_url, admin_token):
        """Impersonated partner can view user detail for a submitted user."""
        with httpx.Client(timeout=15) as c:
            users = c.get(f"{base_url}/api/admin/users", headers=auth(admin_token)).json()
            partner_user = next(u for u in users if u["email"] == "partner@example.com")

            imp_token = c.post(f"{base_url}/api/admin/impersonate/{partner_user['id']}", headers=auth(admin_token)).json()["access_token"]

            subs = c.get(f"{base_url}/api/partner/submissions", headers=auth(imp_token)).json()
            assert len(subs) > 0

            user_id = subs[0]["user_id"]
            r = c.get(f"{base_url}/api/partner/users/{user_id}", headers=auth(imp_token))
            assert r.status_code == 200
            assert "progress" in r.json()
            assert "steps" in r.json()

    def test_impersonate_different_partners(self, base_url, admin_token):
        """Admin can impersonate different partner users sequentially."""
        with httpx.Client(timeout=15) as c:
            users = c.get(f"{base_url}/api/admin/users", headers=auth(admin_token)).json()
            partner_users = [u for u in users if u["role"] == "partner"]
            assert len(partner_users) >= 2

            for pu in partner_users[:3]:
                r = c.post(f"{base_url}/api/admin/impersonate/{pu['id']}", headers=auth(admin_token))
                assert r.status_code == 200
                imp_token = r.json()["access_token"]

                me = c.get(f"{base_url}/api/auth/me", headers=auth(imp_token)).json()
                assert me["email"] == pu["email"]
                assert me["role"] == "partner"
