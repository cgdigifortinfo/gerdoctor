"""
Backend API tests for GERdoctor iteration 13 features:
- GET /api/settings (public endpoint)
- PUT /api/admin/settings (admin only)
- Logo component integration
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin123!"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Demo123!"


class TestSettingsAPI:
    """Test the new settings endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session for tests"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_get_settings_public(self):
        """GET /api/settings should return default settings without auth"""
        response = self.session.get(f"{BASE_URL}/api/settings")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify default settings structure
        assert "site_title" in data, "Missing site_title"
        assert "logo_bold_part" in data, "Missing logo_bold_part"
        assert "logo_light_part" in data, "Missing logo_light_part"
        assert "primary_color" in data, "Missing primary_color"
        
        # Verify default values
        assert data.get("logo_bold_part") == "GER", f"Expected logo_bold_part='GER', got {data.get('logo_bold_part')}"
        assert data.get("logo_light_part") == "doctor", f"Expected logo_light_part='doctor', got {data.get('logo_light_part')}"
        print(f"SUCCESS: GET /api/settings returns correct defaults: {data}")
    
    def test_admin_login(self):
        """Admin login should work with correct credentials"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert data.get("role") == "admin", f"Expected admin role, got {data.get('role')}"
        print(f"SUCCESS: Admin login successful")
        return response.cookies
    
    def test_update_settings_requires_admin(self):
        """PUT /api/admin/settings should require admin auth"""
        # Try without auth
        response = self.session.put(f"{BASE_URL}/api/admin/settings", json={
            "site_title": "Test Title"
        })
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("SUCCESS: PUT /api/admin/settings requires authentication")
    
    def test_update_settings_as_admin(self):
        """PUT /api/admin/settings should work for admin"""
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
        
        # Update settings
        test_settings = {
            "site_title": "GERdoctor Test",
            "logo_bold_part": "GER",
            "logo_light_part": "doctor",
            "contact_email": "test@gerdoctor.de",
            "primary_color": "#114f55",
            "footer_text": "Test Footer",
            "meta_description": "Test Description"
        }
        
        response = self.session.put(f"{BASE_URL}/api/admin/settings", json=test_settings)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("message") == "Settings updated", f"Unexpected response: {data}"
        print("SUCCESS: PUT /api/admin/settings works for admin")
        
        # Verify settings were saved by fetching them
        get_response = self.session.get(f"{BASE_URL}/api/settings")
        assert get_response.status_code == 200
        saved_data = get_response.json()
        assert saved_data.get("site_title") == "GERdoctor Test", f"Settings not persisted: {saved_data}"
        assert saved_data.get("contact_email") == "test@gerdoctor.de"
        print(f"SUCCESS: Settings persisted correctly: {saved_data}")
    
    def test_update_settings_as_regular_user_fails(self):
        """PUT /api/admin/settings should fail for regular user"""
        # Login as demo user
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        assert login_response.status_code == 200, f"Demo user login failed: {login_response.text}"
        
        # Try to update settings
        response = self.session.put(f"{BASE_URL}/api/admin/settings", json={
            "site_title": "Hacked Title"
        })
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("SUCCESS: Regular user cannot update settings (403)")


class TestExistingAPIs:
    """Verify existing APIs still work after changes"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_health_check(self):
        """API root should respond"""
        response = self.session.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        print("SUCCESS: API health check passed")
    
    def test_cms_home_content(self):
        """CMS home content should still work"""
        response = self.session.get(f"{BASE_URL}/api/cms/home")
        assert response.status_code == 200
        data = response.json()
        assert "content" in data or "section" in data
        print(f"SUCCESS: CMS home content works: {data}")
    
    def test_partners_list(self):
        """Partners list should still work"""
        response = self.session.get(f"{BASE_URL}/api/partners")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Partners list works, found {len(data)} partners")
    
    def test_steps_require_auth(self):
        """Steps endpoint should require auth"""
        response = self.session.get(f"{BASE_URL}/api/steps")
        assert response.status_code == 401
        print("SUCCESS: Steps endpoint requires auth")
    
    def test_user_dashboard_flow(self):
        """Test user can login and access steps"""
        # Login as demo user
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD
        })
        assert login_response.status_code == 200, f"Demo login failed: {login_response.text}"
        
        # Get steps
        steps_response = self.session.get(f"{BASE_URL}/api/steps")
        assert steps_response.status_code == 200
        steps = steps_response.json()
        assert len(steps) > 0, "No steps found"
        print(f"SUCCESS: User can access {len(steps)} steps")
        
        # Get progress
        progress_response = self.session.get(f"{BASE_URL}/api/steps/progress")
        assert progress_response.status_code == 200
        print("SUCCESS: User can access progress")
        
        # Get all data (for conditional logic)
        all_data_response = self.session.get(f"{BASE_URL}/api/steps/all-data")
        assert all_data_response.status_code == 200
        print("SUCCESS: User can access all-data endpoint")


class TestAdminDashboard:
    """Test admin dashboard APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
    
    def test_admin_users_list(self):
        """Admin should be able to list users"""
        response = self.session.get(f"{BASE_URL}/api/admin/users")
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) > 0
        # Check user has completion_pct
        assert "completion_pct" in users[0], "Missing completion_pct in user data"
        print(f"SUCCESS: Admin can list {len(users)} users with completion_pct")
    
    def test_admin_steps_list(self):
        """Admin should be able to list steps"""
        response = self.session.get(f"{BASE_URL}/api/admin/steps")
        assert response.status_code == 200
        steps = response.json()
        assert isinstance(steps, list)
        assert len(steps) > 0
        print(f"SUCCESS: Admin can list {len(steps)} steps")
    
    def test_admin_partners_list(self):
        """Admin should be able to list partners"""
        response = self.session.get(f"{BASE_URL}/api/admin/partners")
        assert response.status_code == 200
        partners = response.json()
        assert isinstance(partners, list)
        print(f"SUCCESS: Admin can list {len(partners)} partners")
    
    def test_admin_analytics(self):
        """Admin should be able to get analytics"""
        response = self.session.get(f"{BASE_URL}/api/admin/analytics")
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "step_analytics" in data
        print(f"SUCCESS: Admin analytics works: {data.get('total_users')} users")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
