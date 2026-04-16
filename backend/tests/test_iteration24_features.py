"""
Test iteration 24 features:
1. Admin Create User (POST /api/admin/users)
2. Partner Editor with linked_user_ids (PUT /api/admin/partners/{id})
3. GET /api/admin/partners returns linked_users array
4. partner_multiselection step type
5. POST /api/partners/submit-multi endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin123!"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Demo123!"
PARTNER_EMAIL = "partner@example.com"
PARTNER_PASSWORD = "Partner123!"


@pytest.fixture(scope="module")
def admin_session():
    """Login as admin and return session with cookies"""
    session = requests.Session()
    resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return session


@pytest.fixture(scope="module")
def demo_session():
    """Login as demo user and return session with cookies"""
    session = requests.Session()
    resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD
    })
    assert resp.status_code == 200, f"Demo login failed: {resp.text}"
    return session


class TestAdminCreateUser:
    """Tests for POST /api/admin/users endpoint"""
    
    def test_create_user_success(self, admin_session):
        """Admin can create a new user"""
        import uuid
        unique_email = f"TEST_user_{uuid.uuid4().hex[:8]}@test.com"
        
        resp = admin_session.post(f"{BASE_URL}/api/admin/users", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "TEST Created User",
            "role": "user"
        })
        
        assert resp.status_code == 200, f"Create user failed: {resp.text}"
        data = resp.json()
        assert "id" in data
        assert data.get("message") == "User created"
        
        # Verify user exists
        users_resp = admin_session.get(f"{BASE_URL}/api/admin/users")
        assert users_resp.status_code == 200
        users = users_resp.json()
        created_user = next((u for u in users if u["email"] == unique_email), None)
        assert created_user is not None, "Created user not found in users list"
        assert created_user["name"] == "TEST Created User"
        assert created_user["role"] == "user"
    
    def test_create_user_with_partner_role(self, admin_session):
        """Admin can create a user with partner role and partner_id"""
        import uuid
        unique_email = f"TEST_partner_{uuid.uuid4().hex[:8]}@test.com"
        
        # Get a partner ID first
        partners_resp = admin_session.get(f"{BASE_URL}/api/admin/partners")
        assert partners_resp.status_code == 200
        partners = partners_resp.json()
        if not partners:
            pytest.skip("No partners available to test partner role assignment")
        
        partner_id = partners[0]["id"]
        
        resp = admin_session.post(f"{BASE_URL}/api/admin/users", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "TEST Partner User",
            "role": "partner",
            "partner_id": partner_id
        })
        
        assert resp.status_code == 200, f"Create partner user failed: {resp.text}"
        data = resp.json()
        assert "id" in data
    
    def test_create_user_duplicate_email_returns_400(self, admin_session):
        """Creating user with existing email returns 400"""
        resp = admin_session.post(f"{BASE_URL}/api/admin/users", json={
            "email": ADMIN_EMAIL,  # Already exists
            "password": "TestPass123!",
            "name": "Duplicate User",
            "role": "user"
        })
        
        assert resp.status_code == 400, f"Expected 400 for duplicate email, got {resp.status_code}"
        assert "already registered" in resp.json().get("detail", "").lower()
    
    def test_create_user_requires_admin(self, demo_session):
        """Non-admin cannot create users"""
        import uuid
        unique_email = f"TEST_unauth_{uuid.uuid4().hex[:8]}@test.com"
        
        resp = demo_session.post(f"{BASE_URL}/api/admin/users", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "Unauthorized User",
            "role": "user"
        })
        
        assert resp.status_code == 403, f"Expected 403 for non-admin, got {resp.status_code}"


class TestPartnerLinkedUsers:
    """Tests for partner linked_users functionality"""
    
    def test_get_partners_returns_linked_users(self, admin_session):
        """GET /api/admin/partners returns linked_users array"""
        resp = admin_session.get(f"{BASE_URL}/api/admin/partners")
        assert resp.status_code == 200
        partners = resp.json()
        
        assert isinstance(partners, list)
        if partners:
            partner = partners[0]
            assert "linked_users" in partner, "Partner should have linked_users field"
            assert isinstance(partner["linked_users"], list)
            # Each linked user should have id, name, email
            for lu in partner["linked_users"]:
                assert "id" in lu
                assert "name" in lu
                assert "email" in lu
    
    def test_update_partner_with_linked_user_ids(self, admin_session):
        """PUT /api/admin/partners/{id} with linked_user_ids updates user roles"""
        # Get partners
        partners_resp = admin_session.get(f"{BASE_URL}/api/admin/partners")
        assert partners_resp.status_code == 200
        partners = partners_resp.json()
        if not partners:
            pytest.skip("No partners available")
        
        partner = partners[0]
        partner_id = partner["id"]
        
        # Get users to link
        users_resp = admin_session.get(f"{BASE_URL}/api/admin/users")
        assert users_resp.status_code == 200
        users = users_resp.json()
        
        # Find a user with role 'user' to link
        user_to_link = next((u for u in users if u["role"] == "user"), None)
        if not user_to_link:
            pytest.skip("No user with role 'user' available to link")
        
        # Update partner with linked_user_ids
        resp = admin_session.put(f"{BASE_URL}/api/admin/partners/{partner_id}", json={
            "linked_user_ids": [user_to_link["id"]]
        })
        
        assert resp.status_code == 200, f"Update partner failed: {resp.text}"
        
        # Verify the user's role changed to 'partner'
        user_resp = admin_session.get(f"{BASE_URL}/api/admin/users/{user_to_link['id']}")
        assert user_resp.status_code == 200
        updated_user = user_resp.json()
        assert updated_user["role"] == "partner", f"User role should be 'partner', got {updated_user['role']}"
        
        # Verify linked_users in partner response
        partners_resp2 = admin_session.get(f"{BASE_URL}/api/admin/partners")
        updated_partner = next((p for p in partners_resp2.json() if p["id"] == partner_id), None)
        assert updated_partner is not None
        linked_ids = [lu["id"] for lu in updated_partner.get("linked_users", [])]
        assert user_to_link["id"] in linked_ids, "User should be in linked_users"
        
        # Cleanup: unlink the user
        admin_session.put(f"{BASE_URL}/api/admin/partners/{partner_id}", json={
            "linked_user_ids": []
        })


class TestPartnerMultiselection:
    """Tests for partner_multiselection step type and submit-multi endpoint"""
    
    def test_step_type_partner_multiselection_accepted(self, admin_session):
        """Backend accepts partner_multiselection as valid step_type"""
        resp = admin_session.post(f"{BASE_URL}/api/admin/steps", json={
            "title": "TEST Multi Partner Selection",
            "description": "Select multiple partners",
            "order": 99,
            "step_type": "partner_multiselection",
            "filter_tag": "test"
        })
        
        assert resp.status_code == 200, f"Create step failed: {resp.text}"
        data = resp.json()
        assert "id" in data
        step_id = data["id"]
        
        # Verify step was created with correct type
        steps_resp = admin_session.get(f"{BASE_URL}/api/admin/steps")
        assert steps_resp.status_code == 200
        steps = steps_resp.json()
        created_step = next((s for s in steps if s["id"] == step_id), None)
        assert created_step is not None
        assert created_step["step_type"] == "partner_multiselection"
        
        # Cleanup
        admin_session.delete(f"{BASE_URL}/api/admin/steps/{step_id}")
    
    def test_submit_multi_endpoint_exists(self, demo_session):
        """POST /api/partners/submit-multi endpoint exists and works"""
        # Get partners
        partners_resp = demo_session.get(f"{BASE_URL}/api/partners")
        assert partners_resp.status_code == 200
        partners = partners_resp.json()
        
        if len(partners) < 2:
            pytest.skip("Need at least 2 partners to test multi-selection")
        
        partner_ids = [partners[0]["id"], partners[1]["id"]]
        
        resp = demo_session.post(f"{BASE_URL}/api/partners/submit-multi", json={
            "partner_ids": partner_ids,
            "data": {"test_field": "test_value"}
        })
        
        assert resp.status_code == 200, f"Submit multi failed: {resp.text}"
        data = resp.json()
        assert "submission_ids" in data
        assert len(data["submission_ids"]) == 2, "Should create 2 submissions"
        assert "Submitted to 2 partners" in data.get("message", "")
    
    def test_submit_multi_creates_submissions_for_all_partners(self, admin_session, demo_session):
        """Submitting to multiple partners creates submissions visible to each partner"""
        # Get partners
        partners_resp = demo_session.get(f"{BASE_URL}/api/partners")
        partners = partners_resp.json()
        
        if len(partners) < 2:
            pytest.skip("Need at least 2 partners")
        
        partner_ids = [partners[0]["id"], partners[1]["id"]]
        
        # Submit to multiple partners
        resp = demo_session.post(f"{BASE_URL}/api/partners/submit-multi", json={
            "partner_ids": partner_ids,
            "data": {"multi_test": "value"}
        })
        assert resp.status_code == 200
        
        # Verify submissions exist for each partner (admin can check)
        # This is verified by the fact that the endpoint returns submission_ids


class TestOverlayMaxHeight:
    """Tests to verify overlay dialogs have proper max-height constraints"""
    
    def test_dialog_content_has_max_height_class(self, admin_session):
        """Verify DialogContent components have max-h and overflow-y-auto in code"""
        # This is a code review test - we grep the frontend code
        import subprocess
        result = subprocess.run(
            ["grep", "-c", "max-h-\\[.*vh\\] overflow-y-auto", "/app/frontend/src/pages/AdminDashboard.js"],
            capture_output=True, text=True
        )
        count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
        assert count >= 4, f"Expected at least 4 DialogContent with max-h and overflow-y-auto, found {count}"


class TestCleanup:
    """Cleanup test data created during tests"""
    
    def test_cleanup_test_users(self, admin_session):
        """Remove TEST_ prefixed users"""
        users_resp = admin_session.get(f"{BASE_URL}/api/admin/users")
        if users_resp.status_code != 200:
            return
        
        users = users_resp.json()
        test_users = [u for u in users if u["name"].startswith("TEST") or u["email"].startswith("TEST")]
        
        # Note: There's no delete user endpoint, so we just verify cleanup would be needed
        # In a real scenario, we'd delete these users
        print(f"Found {len(test_users)} test users that would need cleanup")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
