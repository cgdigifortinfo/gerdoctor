"""
Test suite for Admin Impersonation feature (Iteration 20)
Tests:
1. POST /api/admin/impersonate/{user_id} - Admin can impersonate users
2. Non-admin cannot impersonate
3. Returns access_token and user object
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAdminImpersonation:
    """Test admin impersonation endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.admin_email = "admin@example.com"
        self.admin_password = "Admin123!"
        self.demo_email = "demo@example.com"
        self.demo_password = "Demo123!"
        self.partner_email = "partner@example.com"
        self.partner_password = "Partner123!"
        self.session = requests.Session()
    
    def get_admin_token(self):
        """Login as admin and get token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("access_token")
    
    def get_user_token(self):
        """Login as regular user and get token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.demo_email,
            "password": self.demo_password
        })
        assert response.status_code == 200, f"User login failed: {response.text}"
        return response.json().get("access_token")
    
    def get_all_users(self, token):
        """Get all users as admin"""
        response = self.session.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        return response.json()
    
    def test_admin_can_impersonate_user(self):
        """Test that admin can impersonate a regular user"""
        admin_token = self.get_admin_token()
        users = self.get_all_users(admin_token)
        
        # Find demo user
        demo_user = next((u for u in users if u["email"] == self.demo_email), None)
        assert demo_user is not None, "Demo user not found"
        
        # Impersonate demo user
        response = self.session.post(
            f"{BASE_URL}/api/admin/impersonate/{demo_user['id']}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Impersonate failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data, "Response missing access_token"
        assert "user" in data, "Response missing user object"
        assert data["user"]["email"] == self.demo_email
        assert data["user"]["role"] == "user"
        assert "id" in data["user"]
        assert "name" in data["user"]
        
        print(f"✓ Admin successfully impersonated user: {data['user']['email']}")
    
    def test_admin_can_impersonate_partner(self):
        """Test that admin can impersonate a partner user"""
        admin_token = self.get_admin_token()
        users = self.get_all_users(admin_token)
        
        # Find partner user
        partner_user = next((u for u in users if u["email"] == self.partner_email), None)
        assert partner_user is not None, "Partner user not found"
        
        # Impersonate partner user
        response = self.session.post(
            f"{BASE_URL}/api/admin/impersonate/{partner_user['id']}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Impersonate partner failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == self.partner_email
        assert data["user"]["role"] == "partner"
        
        print(f"✓ Admin successfully impersonated partner: {data['user']['email']}")
    
    def test_impersonated_token_works(self):
        """Test that the impersonated token can be used to access user data"""
        admin_token = self.get_admin_token()
        users = self.get_all_users(admin_token)
        
        # Find demo user
        demo_user = next((u for u in users if u["email"] == self.demo_email), None)
        assert demo_user is not None
        
        # Impersonate
        response = self.session.post(
            f"{BASE_URL}/api/admin/impersonate/{demo_user['id']}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        impersonated_token = response.json()["access_token"]
        
        # Use impersonated token to access /auth/me - use NEW session without cookies
        new_session = requests.Session()
        me_response = new_session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {impersonated_token}"}
        )
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["email"] == self.demo_email
        
        print(f"✓ Impersonated token works - /auth/me returns: {me_data['email']}")
    
    def test_non_admin_cannot_impersonate(self):
        """Test that regular users cannot impersonate"""
        # Use separate session for user login to avoid cookie contamination
        user_session = requests.Session()
        user_response = user_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.demo_email,
            "password": self.demo_password
        })
        assert user_response.status_code == 200
        user_token = user_response.json().get("access_token")
        
        # Get users list with admin token (separate session)
        admin_session = requests.Session()
        admin_response = admin_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        admin_token = admin_response.json().get("access_token")
        users_response = admin_session.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        users = users_response.json()
        
        # Find any user to try to impersonate
        target_user = next((u for u in users if u["email"] != self.demo_email), None)
        assert target_user is not None
        
        # Try to impersonate as regular user - use fresh session with only user token
        fresh_session = requests.Session()
        response = fresh_session.post(
            f"{BASE_URL}/api/admin/impersonate/{target_user['id']}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("✓ Non-admin correctly denied impersonation (403)")
    
    def test_impersonate_nonexistent_user(self):
        """Test impersonating a non-existent user returns 404"""
        admin_token = self.get_admin_token()
        
        # Try to impersonate non-existent user
        fake_id = "000000000000000000000000"
        response = self.session.post(
            f"{BASE_URL}/api/admin/impersonate/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Impersonating non-existent user returns 404")
    
    def test_impersonate_creates_audit_log(self):
        """Test that impersonation creates an audit log entry"""
        admin_token = self.get_admin_token()
        users = self.get_all_users(admin_token)
        
        # Find demo user
        demo_user = next((u for u in users if u["email"] == self.demo_email), None)
        assert demo_user is not None
        
        # Impersonate
        response = self.session.post(
            f"{BASE_URL}/api/admin/impersonate/{demo_user['id']}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        # Check audit log
        audit_response = self.session.get(
            f"{BASE_URL}/api/admin/audit-log?limit=10",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert audit_response.status_code == 200
        logs = audit_response.json().get("logs", [])
        
        # Find impersonate action
        impersonate_log = next((l for l in logs if l.get("action") == "impersonate"), None)
        assert impersonate_log is not None, "Impersonate audit log not found"
        assert impersonate_log["target_type"] == "user"
        assert impersonate_log["target_id"] == demo_user["id"]
        
        print(f"✓ Impersonation audit log created: {impersonate_log}")


class TestEstimatedCompletionInHeader:
    """Test estimated completion endpoint for header display"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.demo_email = "demo@example.com"
        self.demo_password = "Demo123!"
        self.session = requests.Session()
    
    def get_user_token(self):
        """Login as user and get token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.demo_email,
            "password": self.demo_password
        })
        assert response.status_code == 200
        return response.json().get("access_token")
    
    def test_estimated_completion_endpoint(self):
        """Test GET /api/steps/estimated-completion returns valid date"""
        token = self.get_user_token()
        
        response = self.session.get(
            f"{BASE_URL}/api/steps/estimated-completion",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "estimated_completion" in data
        assert data["estimated_completion"] is not None
        
        # Verify it's a valid ISO date
        from datetime import datetime
        try:
            datetime.fromisoformat(data["estimated_completion"].replace("Z", "+00:00"))
            print(f"✓ Estimated completion date: {data['estimated_completion']}")
        except ValueError:
            pytest.fail(f"Invalid date format: {data['estimated_completion']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
