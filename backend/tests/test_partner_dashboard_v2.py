"""
Test Partner Dashboard Enhancement Features (Iteration 23)
- GET /api/partner/submissions returns completion_pct and field_of_study
- GET /api/partner/other-users returns users not submitted to this partner
- Sorting and filtering data validation
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPartnerDashboardEnhancements:
    """Test new Partner Dashboard features: tabs, progress, field_of_study"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as partner user"""
        self.session = requests.Session()
        # Login as partner
        resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@example.com",
            "password": "Partner123!"
        })
        assert resp.status_code == 200, f"Partner login failed: {resp.text}"
        self.partner_token = resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.partner_token}"})
        yield
        # Logout
        self.session.post(f"{BASE_URL}/api/auth/logout")
    
    def test_partner_submissions_returns_completion_pct(self):
        """GET /api/partner/submissions should include completion_pct field"""
        resp = self.session.get(f"{BASE_URL}/api/partner/submissions")
        assert resp.status_code == 200, f"Failed to get submissions: {resp.text}"
        
        submissions = resp.json()
        assert isinstance(submissions, list), "Submissions should be a list"
        
        # Check that each submission has completion_pct
        for sub in submissions:
            assert "completion_pct" in sub, f"Missing completion_pct in submission: {sub}"
            assert isinstance(sub["completion_pct"], (int, float)), f"completion_pct should be numeric: {sub['completion_pct']}"
            assert 0 <= sub["completion_pct"] <= 100, f"completion_pct should be 0-100: {sub['completion_pct']}"
            print(f"User {sub.get('user_name')}: {sub['completion_pct']}% complete")
    
    def test_partner_submissions_returns_field_of_study(self):
        """GET /api/partner/submissions should include field_of_study field"""
        resp = self.session.get(f"{BASE_URL}/api/partner/submissions")
        assert resp.status_code == 200, f"Failed to get submissions: {resp.text}"
        
        submissions = resp.json()
        for sub in submissions:
            assert "field_of_study" in sub, f"Missing field_of_study in submission: {sub}"
            # field_of_study can be empty string if not set
            print(f"User {sub.get('user_name')}: field_of_study='{sub['field_of_study']}'")
    
    def test_partner_submissions_returns_estimated_completion(self):
        """GET /api/partner/submissions should include estimated_completion field"""
        resp = self.session.get(f"{BASE_URL}/api/partner/submissions")
        assert resp.status_code == 200, f"Failed to get submissions: {resp.text}"
        
        submissions = resp.json()
        for sub in submissions:
            assert "estimated_completion" in sub, f"Missing estimated_completion in submission: {sub}"
            print(f"User {sub.get('user_name')}: forecast={sub['estimated_completion']}")
    
    def test_partner_other_users_endpoint_exists(self):
        """GET /api/partner/other-users should return users not submitted to this partner"""
        resp = self.session.get(f"{BASE_URL}/api/partner/other-users")
        assert resp.status_code == 200, f"Failed to get other users: {resp.text}"
        
        other_users = resp.json()
        assert isinstance(other_users, list), "Other users should be a list"
        print(f"Found {len(other_users)} other users")
    
    def test_partner_other_users_has_required_fields(self):
        """GET /api/partner/other-users should return users with required fields"""
        resp = self.session.get(f"{BASE_URL}/api/partner/other-users")
        assert resp.status_code == 200
        
        other_users = resp.json()
        required_fields = ["user_id", "user_name", "user_email", "completion_pct", "estimated_completion", "field_of_study"]
        
        for user in other_users:
            for field in required_fields:
                assert field in user, f"Missing field '{field}' in other user: {user}"
            print(f"Other user: {user['user_name']} ({user['user_email']}), {user['completion_pct']}%")
    
    def test_partner_other_users_excludes_submitted_users(self):
        """Other users should NOT include users who submitted to this partner"""
        # Get submissions
        subs_resp = self.session.get(f"{BASE_URL}/api/partner/submissions")
        assert subs_resp.status_code == 200
        submissions = subs_resp.json()
        submitted_user_ids = {sub["user_id"] for sub in submissions}
        
        # Get other users
        other_resp = self.session.get(f"{BASE_URL}/api/partner/other-users")
        assert other_resp.status_code == 200
        other_users = other_resp.json()
        other_user_ids = {u["user_id"] for u in other_users}
        
        # Verify no overlap
        overlap = submitted_user_ids & other_user_ids
        assert len(overlap) == 0, f"Users appear in both lists: {overlap}"
        print(f"Verified: {len(submitted_user_ids)} submitted users, {len(other_user_ids)} other users, no overlap")
    
    def test_partner_profile_endpoint(self):
        """GET /api/partner/profile should return partner profile"""
        resp = self.session.get(f"{BASE_URL}/api/partner/profile")
        assert resp.status_code == 200, f"Failed to get partner profile: {resp.text}"
        
        profile = resp.json()
        assert "id" in profile
        assert "name" in profile
        print(f"Partner profile: {profile['name']}")
    
    def test_partner_user_detail_for_submitted_user(self):
        """Partner can view details of users who submitted to them"""
        # Get a submitted user
        subs_resp = self.session.get(f"{BASE_URL}/api/partner/submissions")
        assert subs_resp.status_code == 200
        submissions = subs_resp.json()
        
        if not submissions:
            pytest.skip("No submissions to test user detail")
        
        user_id = submissions[0]["user_id"]
        detail_resp = self.session.get(f"{BASE_URL}/api/partner/users/{user_id}")
        assert detail_resp.status_code == 200, f"Failed to get user detail: {detail_resp.text}"
        
        detail = detail_resp.json()
        assert "id" in detail
        assert "name" in detail
        assert "email" in detail
        assert "progress" in detail
        assert "steps" in detail
        assert "completion_pct" in detail
        print(f"User detail: {detail['name']}, {detail['completion_pct']}% complete")
    
    def test_partner_user_detail_denied_for_non_submitted_user(self):
        """Partner cannot view details of users who did NOT submit to them"""
        # Get other users
        other_resp = self.session.get(f"{BASE_URL}/api/partner/other-users")
        assert other_resp.status_code == 200
        other_users = other_resp.json()
        
        if not other_users:
            pytest.skip("No other users to test access denial")
        
        user_id = other_users[0]["user_id"]
        detail_resp = self.session.get(f"{BASE_URL}/api/partner/users/{user_id}")
        assert detail_resp.status_code == 403, f"Expected 403 for non-submitted user, got {detail_resp.status_code}"
        print(f"Correctly denied access to non-submitted user {user_id}")


class TestPartnerDashboardAsNonPartner:
    """Test that non-partner users cannot access partner endpoints"""
    
    def test_regular_user_cannot_access_partner_submissions(self):
        """Regular user should get 403 on partner endpoints"""
        session = requests.Session()
        # Login as regular user
        resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Demo123!"
        })
        assert resp.status_code == 200, f"Demo login failed: {resp.text}"
        
        # Try to access partner submissions
        subs_resp = session.get(f"{BASE_URL}/api/partner/submissions")
        assert subs_resp.status_code == 403, f"Expected 403, got {subs_resp.status_code}"
        print("Regular user correctly denied access to partner submissions")
        
        session.post(f"{BASE_URL}/api/auth/logout")
    
    def test_regular_user_cannot_access_other_users(self):
        """Regular user should get 403 on partner other-users endpoint"""
        session = requests.Session()
        resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "demo@example.com",
            "password": "Demo123!"
        })
        assert resp.status_code == 200
        
        other_resp = session.get(f"{BASE_URL}/api/partner/other-users")
        assert other_resp.status_code == 403, f"Expected 403, got {other_resp.status_code}"
        print("Regular user correctly denied access to partner other-users")
        
        session.post(f"{BASE_URL}/api/auth/logout")


class TestDataIntegrity:
    """Test data integrity for sorting/filtering"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as partner user"""
        self.session = requests.Session()
        resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@example.com",
            "password": "Partner123!"
        })
        assert resp.status_code == 200
        self.partner_token = resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.partner_token}"})
        yield
        self.session.post(f"{BASE_URL}/api/auth/logout")
    
    def test_completion_pct_is_sortable(self):
        """completion_pct values should be numeric and sortable"""
        resp = self.session.get(f"{BASE_URL}/api/partner/submissions")
        assert resp.status_code == 200
        
        submissions = resp.json()
        pcts = [sub["completion_pct"] for sub in submissions]
        
        # Verify all are numeric
        for pct in pcts:
            assert isinstance(pct, (int, float)), f"Non-numeric completion_pct: {pct}"
        
        # Verify sorting works
        sorted_asc = sorted(pcts)
        sorted_desc = sorted(pcts, reverse=True)
        print(f"Completion percentages: {pcts}")
        print(f"Sorted asc: {sorted_asc}")
        print(f"Sorted desc: {sorted_desc}")
    
    def test_estimated_completion_is_sortable(self):
        """estimated_completion values should be ISO dates and sortable"""
        resp = self.session.get(f"{BASE_URL}/api/partner/submissions")
        assert resp.status_code == 200
        
        submissions = resp.json()
        dates = [sub["estimated_completion"] for sub in submissions if sub.get("estimated_completion")]
        
        # Verify all are valid ISO dates
        from datetime import datetime
        for d in dates:
            try:
                datetime.fromisoformat(d.replace("Z", "+00:00"))
            except ValueError:
                pytest.fail(f"Invalid date format: {d}")
        
        print(f"Forecast dates: {dates}")
    
    def test_field_of_study_is_filterable(self):
        """field_of_study values should be strings suitable for filtering"""
        resp = self.session.get(f"{BASE_URL}/api/partner/submissions")
        assert resp.status_code == 200
        
        submissions = resp.json()
        fields = [sub["field_of_study"] for sub in submissions]
        
        # Verify all are strings
        for f in fields:
            assert isinstance(f, str), f"Non-string field_of_study: {f}"
        
        # Get unique values
        unique_fields = set(f for f in fields if f)
        print(f"Unique Fachgebiete: {unique_fields}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
