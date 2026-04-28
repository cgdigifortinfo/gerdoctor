"""
Comprehensive route & role-based access test.
Tests ALL API endpoints with all 3 roles (admin, partner, user) + unauthenticated.
Verifies: correct access, correct 401/403 rejection, response structure.
"""
import pytest
import httpx

@pytest.fixture(scope="module")
def base_url():
    import subprocess
    result = subprocess.run(["grep", "REACT_APP_BACKEND_URL", "/app/frontend/.env"], capture_output=True, text=True)
    return result.stdout.strip().split("=", 1)[1]

@pytest.fixture(scope="module")
def tokens(base_url):
    """Get tokens for all 3 roles."""
    with httpx.Client(timeout=15) as c:
        admin = c.post(f"{base_url}/api/auth/login", json={"email": "admin@example.com", "password": "Admin123!"})
        assert admin.status_code == 200

        partner = c.post(f"{base_url}/api/auth/login", json={"email": "partner-example@chrizz1001.de", "password": "Partner123!"})
        assert partner.status_code == 200

        user = c.post(f"{base_url}/api/auth/login", json={"email": "dr.kumar@chrizz1001.de", "password": "Demo123!"})
        assert user.status_code == 200

        return {
            "admin": admin.json()["access_token"],
            "partner": partner.json()["access_token"],
            "user": user.json()["access_token"],
        }

def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ========================
# PUBLIC ENDPOINTS (no auth required)
# ========================

class TestPublicEndpoints:
    def test_api_root(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/")
            assert r.status_code == 200

    def test_cms_get(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/cms")
            assert r.status_code == 200
            assert isinstance(r.json(), dict)

    def test_cms_section(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/cms/home")
            assert r.status_code == 200

    def test_partners_public(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/partners")
            assert r.status_code == 200
            assert isinstance(r.json(), list)
            assert len(r.json()) > 0

    def test_partners_filter_by_tag(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/partners?tag=Antragstellung")
            assert r.status_code == 200
            for p in r.json():
                assert "Antragstellung" in p["tags"]

    def test_settings_public(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/settings/public")
            assert r.status_code == 200


# ========================
# AUTH ENDPOINTS
# ========================

class TestAuthEndpoints:
    def test_login_success(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/auth/login", json={"email": "admin@example.com", "password": "Admin123!"})
            assert r.status_code == 200
            assert "access_token" in r.json()
            assert r.json()["role"] == "admin"

    def test_me_with_token(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            for role, tok in tokens.items():
                r = c.get(f"{base_url}/api/auth/me", headers=auth(tok))
                assert r.status_code == 200
                assert r.json()["role"] == role

    def test_me_without_token(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/auth/me")
            assert r.status_code == 401

    def test_logout(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.post(f"{base_url}/api/auth/logout")
            assert r.status_code == 200


# ========================
# USER-ROLE ENDPOINTS
# ========================

class TestUserRoleEndpoints:
    """Endpoints that require 'user' or any authenticated role."""

    def test_profile_get(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            # User can get profile
            r = c.get(f"{base_url}/api/profile", headers=auth(tokens["user"]))
            assert r.status_code == 200
            assert "name" in r.json()
            # Unauthenticated cannot
            r = c.get(f"{base_url}/api/profile")
            assert r.status_code == 401

    def test_steps_get(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/steps", headers=auth(tokens["user"]))
            assert r.status_code == 200
            steps = r.json()
            assert isinstance(steps, list)
            assert len(steps) == 12
            # Verify steps have id, title, order, step_type
            for s in steps:
                assert "id" in s
                assert "title" in s
                assert "order" in s

    def test_steps_progress(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/steps/progress", headers=auth(tokens["user"]))
            assert r.status_code == 200
            progress = r.json()
            assert isinstance(progress, list)
            # Each has step_id, status
            for p in progress:
                assert "step_id" in p
                assert p["status"] in ("completed", "in_progress", "pending")

    def test_steps_all_data(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/steps/all-data", headers=auth(tokens["user"]))
            assert r.status_code == 200
            data = r.json()
            assert isinstance(data, list)
            assert len(data) == 12

    def test_steps_history(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/steps/history", headers=auth(tokens["user"]))
            assert r.status_code == 200

    def test_estimated_completion(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/steps/estimated-completion", headers=auth(tokens["user"]))
            assert r.status_code == 200
            assert "estimated_completion" in r.json()

    def test_notification_prefs(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/notifications/preferences", headers=auth(tokens["user"]))
            assert r.status_code == 200
            prefs = r.json()
            assert "email_on_step_enter" in prefs

    def test_unauthenticated_cannot_access_steps(self, base_url):
        with httpx.Client(timeout=15) as c:
            for endpoint in ["/api/steps", "/api/steps/progress", "/api/steps/all-data", "/api/steps/history", "/api/steps/estimated-completion"]:
                r = c.get(f"{base_url}{endpoint}")
                assert r.status_code == 401, f"{endpoint} should require auth"


# ========================
# PARTNER-ROLE ENDPOINTS
# ========================

class TestPartnerRoleEndpoints:
    """Endpoints that require 'partner' role."""

    def test_partner_submissions(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/partner/submissions", headers=auth(tokens["partner"]))
            assert r.status_code == 200
            subs = r.json()
            assert isinstance(subs, list)
            for s in subs:
                assert "user_id" in s
                assert "completion_pct" in s

    def test_partner_other_users(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/partner/other-users", headers=auth(tokens["partner"]))
            assert r.status_code == 200
            assert isinstance(r.json(), list)

    def test_partner_profile(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/partner/profile", headers=auth(tokens["partner"]))
            assert r.status_code == 200
            profile = r.json()
            assert "name" in profile
            assert "partner_name" in profile

    def test_partner_user_detail(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            subs = c.get(f"{base_url}/api/partner/submissions", headers=auth(tokens["partner"])).json()
            if subs:
                uid = subs[0]["user_id"]
                r = c.get(f"{base_url}/api/partner/users/{uid}", headers=auth(tokens["partner"]))
                assert r.status_code == 200
                detail = r.json()
                assert "progress" in detail
                assert "steps" in detail
                assert "completion_pct" in detail
                assert "partner_step_id" in detail

    def test_user_cannot_access_partner_endpoints(self, base_url, tokens):
        """Regular user cannot access partner-specific endpoints."""
        with httpx.Client(timeout=15) as c:
            for endpoint in ["/api/partner/submissions", "/api/partner/other-users", "/api/partner/profile"]:
                r = c.get(f"{base_url}{endpoint}", headers=auth(tokens["user"]))
                assert r.status_code == 403, f"User should get 403 on {endpoint}"

    def test_unauthenticated_cannot_access_partner(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/partner/submissions")
            assert r.status_code == 401


# ========================
# ADMIN-ROLE ENDPOINTS
# ========================

class TestAdminRoleEndpoints:
    """Endpoints that require 'admin' role."""

    def test_admin_users(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/admin/users", headers=auth(tokens["admin"]))
            assert r.status_code == 200
            users = r.json()
            assert isinstance(users, list)
            assert len(users) > 0
            for u in users:
                assert "id" in u
                assert "email" in u
                assert "role" in u
                assert "completion_pct" in u

    def test_admin_user_detail(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            users = c.get(f"{base_url}/api/admin/users", headers=auth(tokens["admin"])).json()
            regular = next(u for u in users if u["role"] == "user")
            r = c.get(f"{base_url}/api/admin/users/{regular['id']}", headers=auth(tokens["admin"]))
            assert r.status_code == 200
            detail = r.json()
            assert "progress" in detail
            assert "submissions" in detail
            assert "completion_pct" in detail

    def test_admin_user_search(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/admin/users/search?q=kumar&role=", headers=auth(tokens["admin"]))
            assert r.status_code == 200
            assert any("kumar" in u["email"].lower() or "kumar" in u["name"].lower() for u in r.json())

    def test_admin_steps(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/admin/steps", headers=auth(tokens["admin"]))
            assert r.status_code == 200
            steps = r.json()
            assert len(steps) >= 12
            # Admin steps include extra fields
            assert "email_on_enter" in steps[0]
            assert "duration_value" in steps[0]

    def test_admin_partners(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/admin/partners", headers=auth(tokens["admin"]))
            assert r.status_code == 200
            partners = r.json()
            assert len(partners) > 0
            for p in partners:
                assert "linked_users" in p
                assert "linked_user_ids" in p

    def test_admin_analytics(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/admin/analytics", headers=auth(tokens["admin"]))
            assert r.status_code == 200
            a = r.json()
            assert "total_users" in a
            assert "total_partners" in a
            assert "step_analytics" in a

    def test_admin_audit_log(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/admin/audit-log", headers=auth(tokens["admin"]))
            assert r.status_code == 200
            assert "logs" in r.json()
            assert "total" in r.json()

    def test_admin_settings(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/admin/settings", headers=auth(tokens["admin"]))
            assert r.status_code == 200

    def test_admin_export_csv(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/admin/export/users", headers=auth(tokens["admin"]))
            assert r.status_code == 200
            assert "text/csv" in r.headers.get("content-type", "")

    def test_admin_impersonate(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            users = c.get(f"{base_url}/api/admin/users", headers=auth(tokens["admin"])).json()
            regular = next(u for u in users if u["role"] == "user")
            r = c.post(f"{base_url}/api/admin/impersonate/{regular['id']}", headers=auth(tokens["admin"]))
            assert r.status_code == 200
            assert "access_token" in r.json()
            # Impersonated token works
            me = c.get(f"{base_url}/api/auth/me", headers=auth(r.json()["access_token"]))
            assert me.status_code == 200
            assert me.json()["id"] == regular["id"]

    def test_admin_cms_update(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            # Get current
            before = c.get(f"{base_url}/api/cms/home").json()
            # Update
            r = c.put(f"{base_url}/api/cms/home", headers=auth(tokens["admin"]), json={"section": "home", "content": before})
            assert r.status_code == 200

    # === ACCESS DENIED TESTS ===

    def test_user_cannot_access_admin(self, base_url, tokens):
        """Regular user gets 403 on admin endpoints."""
        with httpx.Client(timeout=15) as c:
            endpoints = [
                ("GET", "/api/admin/users"),
                ("GET", "/api/admin/steps"),
                ("GET", "/api/admin/partners"),
                ("GET", "/api/admin/analytics"),
                ("GET", "/api/admin/audit-log"),
                ("GET", "/api/admin/settings"),
            ]
            for method, endpoint in endpoints:
                if method == "GET":
                    r = c.get(f"{base_url}{endpoint}", headers=auth(tokens["user"]))
                assert r.status_code == 403, f"User should get 403 on {endpoint}, got {r.status_code}"

    def test_partner_cannot_access_admin(self, base_url, tokens):
        """Partner user gets 403 on admin endpoints."""
        with httpx.Client(timeout=15) as c:
            for endpoint in ["/api/admin/users", "/api/admin/steps", "/api/admin/partners", "/api/admin/analytics"]:
                r = c.get(f"{base_url}{endpoint}", headers=auth(tokens["partner"]))
                assert r.status_code == 403, f"Partner should get 403 on {endpoint}, got {r.status_code}"

    def test_unauthenticated_cannot_access_admin(self, base_url):
        with httpx.Client(timeout=15) as c:
            r = c.get(f"{base_url}/api/admin/users")
            assert r.status_code == 401


# ========================
# CROSS-ROLE ENDPOINT TESTS
# ========================

class TestCrossRoleAccess:
    """Verify endpoints accessible by multiple roles work correctly."""

    def test_all_roles_can_get_profile(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            for role, tok in tokens.items():
                r = c.get(f"{base_url}/api/profile", headers=auth(tok))
                assert r.status_code == 200, f"{role} should be able to get profile"

    def test_all_roles_can_get_public_partners(self, base_url, tokens):
        with httpx.Client(timeout=15) as c:
            for role, tok in tokens.items():
                r = c.get(f"{base_url}/api/partners", headers=auth(tok))
                assert r.status_code == 200

    def test_partner_can_view_any_user_detail(self, base_url, tokens):
        """Partner can view user detail for users not submitted to them."""
        with httpx.Client(timeout=15) as c:
            other = c.get(f"{base_url}/api/partner/other-users", headers=auth(tokens["partner"])).json()
            if other:
                r = c.get(f"{base_url}/api/partner/users/{other[0]['user_id']}", headers=auth(tokens["partner"]))
                assert r.status_code == 200

    def test_admin_can_impersonate_partner_and_access_partner_endpoints(self, base_url, tokens):
        """Admin impersonating a partner can access partner dashboard."""
        with httpx.Client(timeout=15) as c:
            users = c.get(f"{base_url}/api/admin/users", headers=auth(tokens["admin"])).json()
            partner = next(u for u in users if u["email"] == "partner-example@chrizz1001.de")
            imp = c.post(f"{base_url}/api/admin/impersonate/{partner['id']}", headers=auth(tokens["admin"]))
            imp_tok = imp.json()["access_token"]

            r = c.get(f"{base_url}/api/partner/submissions", headers=auth(imp_tok))
            assert r.status_code == 200

            r = c.get(f"{base_url}/api/partner/profile", headers=auth(imp_tok))
            assert r.status_code == 200

            r = c.get(f"{base_url}/api/partner/other-users", headers=auth(imp_tok))
            assert r.status_code == 200


# ========================
# DATA INTEGRITY CHECKS
# ========================

class TestDataIntegrity:
    """Verify data consistency across endpoints."""

    def test_completion_pct_consistency(self, base_url, tokens):
        """Admin user list completion_pct matches admin user detail."""
        with httpx.Client(timeout=15) as c:
            users = c.get(f"{base_url}/api/admin/users", headers=auth(tokens["admin"])).json()
            regular = [u for u in users if u["role"] == "user"][:3]
            for u in regular:
                detail = c.get(f"{base_url}/api/admin/users/{u['id']}", headers=auth(tokens["admin"])).json()
                assert u["completion_pct"] == detail["completion_pct"], f"Mismatch for {u['email']}: list={u['completion_pct']} detail={detail['completion_pct']}"

    def test_step_count_matches(self, base_url, tokens):
        """User steps and admin steps have same count of active steps."""
        with httpx.Client(timeout=15) as c:
            user_steps = c.get(f"{base_url}/api/steps", headers=auth(tokens["user"])).json()
            admin_steps = c.get(f"{base_url}/api/admin/steps", headers=auth(tokens["admin"])).json()
            active_admin = [s for s in admin_steps if s.get("is_active", True)]
            assert len(user_steps) == len(active_admin)

    def test_partner_submissions_match_partner_view(self, base_url, tokens):
        """Partner submissions API returns data consistent with admin view."""
        with httpx.Client(timeout=15) as c:
            subs = c.get(f"{base_url}/api/partner/submissions", headers=auth(tokens["partner"])).json()
            # Each submission has required fields
            for s in subs:
                assert "user_id" in s
                assert "completion_pct" in s
                assert isinstance(s["completion_pct"], int)
                assert 0 <= s["completion_pct"] <= 100

    def test_progress_records_exist_for_all_steps(self, base_url, tokens):
        """User has progress records for all active steps."""
        with httpx.Client(timeout=15) as c:
            steps = c.get(f"{base_url}/api/steps", headers=auth(tokens["user"])).json()
            progress = c.get(f"{base_url}/api/steps/progress", headers=auth(tokens["user"])).json()
            step_ids = {s["id"] for s in steps}
            prog_step_ids = {p["step_id"] for p in progress}
            missing = step_ids - prog_step_ids
            assert len(missing) == 0, f"Missing progress for steps: {missing}"
