"""
Test Partner Dashboard API endpoints - Iteration 16
Tests for:
- GET /api/partner/users/{user_id} - Partner can view user step data
- PUT /api/partner/users/{user_id}/progress - Partner can update user step status
- Access control: Partner can only access users who submitted to them
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PARTNER_EMAIL = "partner@example.com"
PARTNER_PASSWORD = "Partner123!"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin123!"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Demo123!"

# Known user with submission to ILS partner (Chris)
CHRIS_USER_ID = "69df40be8f79a5790086315f"


class TestPartnerUserDetailAPI:
    """Test GET /api/partner/users/{user_id} endpoint"""
    
    @pytest.fixture
    def partner_session(self):
        """Login as partner and return session with cookies"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PARTNER_EMAIL, "password": PARTNER_PASSWORD}
        )
        assert response.status_code == 200, f"Partner login failed: {response.text}"
        data = response.json()
        assert data.get("role") == "partner", f"Expected partner role, got {data.get('role')}"
        return session
    
    @pytest.fixture
    def admin_session(self):
        """Login as admin and return session with cookies"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return session
    
    @pytest.fixture
    def demo_session(self):
        """Login as demo user and return session with cookies"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
        )
        assert response.status_code == 200, f"Demo login failed: {response.text}"
        return session
    
    def test_partner_can_get_user_detail_with_submission(self, partner_session):
        """Partner can view user detail for a user who submitted to them"""
        response = partner_session.get(f"{BASE_URL}/api/partner/users/{CHRIS_USER_ID}")
        
        # Should succeed
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "id" in data, "Response should contain user id"
        assert "email" in data, "Response should contain user email"
        assert "name" in data, "Response should contain user name"
        assert "progress" in data, "Response should contain progress array"
        assert "steps" in data, "Response should contain steps array"
        assert "completion_pct" in data, "Response should contain completion_pct"
        
        # Verify data types
        assert isinstance(data["progress"], list), "Progress should be a list"
        assert isinstance(data["steps"], list), "Steps should be a list"
        assert isinstance(data["completion_pct"], (int, float)), "completion_pct should be numeric"
        
        print(f"SUCCESS: Partner can view user {data['name']} ({data['email']})")
        print(f"  - Completion: {data['completion_pct']}%")
        print(f"  - Steps: {len(data['steps'])}")
        print(f"  - Progress entries: {len(data['progress'])}")
    
    def test_partner_cannot_access_user_without_submission(self, partner_session, demo_session):
        """Partner cannot view user detail for a user who did NOT submit to them"""
        # Get demo user's ID
        me_response = demo_session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 200
        demo_user_id = me_response.json()["id"]
        
        # Partner tries to access demo user (who hasn't submitted to ILS)
        response = partner_session.get(f"{BASE_URL}/api/partner/users/{demo_user_id}")
        
        # Should be forbidden
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"SUCCESS: Partner correctly denied access to user without submission")
    
    def test_regular_user_cannot_access_partner_endpoint(self, demo_session):
        """Regular user cannot access partner user detail endpoint"""
        response = demo_session.get(f"{BASE_URL}/api/partner/users/{CHRIS_USER_ID}")
        
        # Should be forbidden (403) or unauthorized
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"SUCCESS: Regular user correctly denied access to partner endpoint")
    
    def test_unauthenticated_cannot_access_partner_endpoint(self):
        """Unauthenticated request cannot access partner user detail endpoint"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/partner/users/{CHRIS_USER_ID}")
        
        # Should be unauthorized
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"SUCCESS: Unauthenticated request correctly denied")


class TestPartnerUpdateProgressAPI:
    """Test PUT /api/partner/users/{user_id}/progress endpoint"""
    
    @pytest.fixture
    def partner_session(self):
        """Login as partner and return session with cookies"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PARTNER_EMAIL, "password": PARTNER_PASSWORD}
        )
        assert response.status_code == 200, f"Partner login failed: {response.text}"
        return session
    
    @pytest.fixture
    def demo_session(self):
        """Login as demo user and return session with cookies"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
        )
        assert response.status_code == 200, f"Demo login failed: {response.text}"
        return session
    
    def test_partner_can_update_user_progress(self, partner_session):
        """Partner can update step status for a user who submitted to them"""
        # First get user detail to find a step ID
        detail_response = partner_session.get(f"{BASE_URL}/api/partner/users/{CHRIS_USER_ID}")
        assert detail_response.status_code == 200
        
        user_data = detail_response.json()
        steps = user_data.get("steps", [])
        assert len(steps) > 0, "User should have steps"
        
        # Get first step ID
        step_id = steps[0]["id"]
        
        # Update progress
        update_response = partner_session.put(
            f"{BASE_URL}/api/partner/users/{CHRIS_USER_ID}/progress",
            json={
                "step_id": step_id,
                "status": "completed",
                "data": {}
            }
        )
        
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        print(f"SUCCESS: Partner can update user progress for step {step_id}")
    
    def test_partner_cannot_update_progress_for_non_submitted_user(self, partner_session, demo_session):
        """Partner cannot update progress for a user who did NOT submit to them"""
        # Get demo user's ID
        me_response = demo_session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 200
        demo_user_id = me_response.json()["id"]
        
        # Partner tries to update demo user's progress
        response = partner_session.put(
            f"{BASE_URL}/api/partner/users/{demo_user_id}/progress",
            json={
                "step_id": "some-step-id",
                "status": "completed",
                "data": {}
            }
        )
        
        # Should be forbidden
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"SUCCESS: Partner correctly denied from updating non-submitted user")
    
    def test_regular_user_cannot_use_partner_update_endpoint(self, demo_session):
        """Regular user cannot use partner update progress endpoint"""
        response = demo_session.put(
            f"{BASE_URL}/api/partner/users/{CHRIS_USER_ID}/progress",
            json={
                "step_id": "some-step-id",
                "status": "completed",
                "data": {}
            }
        )
        
        # Should be forbidden
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"SUCCESS: Regular user correctly denied from partner update endpoint")


class TestAuthLogout:
    """Test logout functionality - single click should work"""
    
    def test_demo_user_logout(self):
        """Demo user can logout with single request"""
        session = requests.Session()
        
        # Login
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        # Verify authenticated
        me_response = session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 200, "Should be authenticated after login"
        
        # Logout (single request)
        logout_response = session.post(f"{BASE_URL}/api/auth/logout")
        assert logout_response.status_code == 200, f"Logout failed: {logout_response.text}"
        
        # Verify no longer authenticated
        me_after_logout = session.get(f"{BASE_URL}/api/auth/me")
        assert me_after_logout.status_code == 401, f"Should be 401 after logout, got {me_after_logout.status_code}"
        
        print("SUCCESS: Demo user logout works with single request")
    
    def test_admin_logout(self):
        """Admin can logout with single request"""
        session = requests.Session()
        
        # Login
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        # Logout
        logout_response = session.post(f"{BASE_URL}/api/auth/logout")
        assert logout_response.status_code == 200
        
        # Verify no longer authenticated
        me_after_logout = session.get(f"{BASE_URL}/api/auth/me")
        assert me_after_logout.status_code == 401, f"Should be 401 after logout, got {me_after_logout.status_code}"
        
        print("SUCCESS: Admin logout works with single request")
    
    def test_partner_logout(self):
        """Partner can logout with single request"""
        session = requests.Session()
        
        # Login
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": PARTNER_EMAIL, "password": PARTNER_PASSWORD}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        # Logout
        logout_response = session.post(f"{BASE_URL}/api/auth/logout")
        assert logout_response.status_code == 200
        
        # Verify no longer authenticated
        me_after_logout = session.get(f"{BASE_URL}/api/auth/me")
        assert me_after_logout.status_code == 401, f"Should be 401 after logout, got {me_after_logout.status_code}"
        
        print("SUCCESS: Partner logout works with single request")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
