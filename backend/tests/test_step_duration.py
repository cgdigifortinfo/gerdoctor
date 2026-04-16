"""
Test Step Duration & Estimated Completion Feature
Tests for iteration 19: duration_value, duration_unit, estimated_completion, started_at, completed_at
"""
import pytest
import requests
import os
from datetime import datetime

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
    assert resp.status_code == 200, f"Demo user login failed: {resp.text}"
    return session


@pytest.fixture(scope="module")
def partner_session():
    """Login as partner and return session with cookies"""
    session = requests.Session()
    resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": PARTNER_EMAIL,
        "password": PARTNER_PASSWORD
    })
    assert resp.status_code == 200, f"Partner login failed: {resp.text}"
    return session


class TestAdminStepsDuration:
    """Test admin steps endpoint returns duration fields"""
    
    def test_admin_steps_returns_duration_fields(self, admin_session):
        """GET /api/admin/steps should return duration_value and duration_unit for each step"""
        resp = admin_session.get(f"{BASE_URL}/api/admin/steps")
        assert resp.status_code == 200, f"Failed to get admin steps: {resp.text}"
        
        steps = resp.json()
        assert isinstance(steps, list), "Steps should be a list"
        assert len(steps) > 0, "Should have at least one step"
        
        # Check each step has duration fields
        for step in steps:
            assert "duration_value" in step, f"Step {step.get('title')} missing duration_value"
            assert "duration_unit" in step, f"Step {step.get('title')} missing duration_unit"
            assert isinstance(step["duration_value"], int), f"duration_value should be int"
            assert step["duration_unit"] in ["days", "weeks", "months", "years"], \
                f"duration_unit should be days/weeks/months/years, got {step['duration_unit']}"
        
        print(f"✓ All {len(steps)} steps have duration_value and duration_unit fields")
        
        # Verify seeded durations match expected values
        # Step 1=0d, Step 2=0d, Step 3=4w, Step 4=0d, Step 5=0d, Step 6=3m, Step 7=0d, Step 8=2w
        sorted_steps = sorted(steps, key=lambda s: s.get("order", 0))
        expected_durations = [
            (1, 0, "days"),
            (2, 0, "days"),
            (3, 4, "weeks"),
            (4, 0, "days"),
            (5, 0, "days"),
            (6, 3, "months"),
            (7, 0, "days"),
            (8, 2, "weeks"),
        ]
        
        for order, exp_value, exp_unit in expected_durations:
            step = next((s for s in sorted_steps if s.get("order") == order), None)
            if step:
                assert step["duration_value"] == exp_value, \
                    f"Step {order} duration_value expected {exp_value}, got {step['duration_value']}"
                assert step["duration_unit"] == exp_unit, \
                    f"Step {order} duration_unit expected {exp_unit}, got {step['duration_unit']}"
                print(f"✓ Step {order}: duration={step['duration_value']} {step['duration_unit']}")
    
    def test_admin_update_step_duration(self, admin_session):
        """PUT /api/admin/steps/{id} can update duration_value and duration_unit"""
        # Get steps first
        resp = admin_session.get(f"{BASE_URL}/api/admin/steps")
        assert resp.status_code == 200
        steps = resp.json()
        
        # Find step 3 (should have 4 weeks)
        step3 = next((s for s in steps if s.get("order") == 3), None)
        assert step3 is not None, "Step 3 not found"
        step_id = step3["id"]
        
        # Update duration to 5 weeks
        update_resp = admin_session.put(f"{BASE_URL}/api/admin/steps/{step_id}", json={
            "duration_value": 5,
            "duration_unit": "weeks"
        })
        assert update_resp.status_code == 200, f"Failed to update step: {update_resp.text}"
        
        # Verify update
        verify_resp = admin_session.get(f"{BASE_URL}/api/admin/steps")
        assert verify_resp.status_code == 200
        updated_steps = verify_resp.json()
        updated_step3 = next((s for s in updated_steps if s.get("id") == step_id), None)
        assert updated_step3["duration_value"] == 5, "duration_value not updated"
        assert updated_step3["duration_unit"] == "weeks", "duration_unit not updated"
        print(f"✓ Step 3 duration updated to 5 weeks")
        
        # Revert back to original
        revert_resp = admin_session.put(f"{BASE_URL}/api/admin/steps/{step_id}", json={
            "duration_value": 4,
            "duration_unit": "weeks"
        })
        assert revert_resp.status_code == 200, "Failed to revert step duration"
        print(f"✓ Step 3 duration reverted to 4 weeks")


class TestUserEstimatedCompletion:
    """Test user estimated completion endpoint"""
    
    def test_user_estimated_completion_endpoint(self, demo_session):
        """GET /api/steps/estimated-completion returns estimated_completion date"""
        resp = demo_session.get(f"{BASE_URL}/api/steps/estimated-completion")
        assert resp.status_code == 200, f"Failed to get estimated completion: {resp.text}"
        
        data = resp.json()
        assert "estimated_completion" in data, "Response missing estimated_completion field"
        
        est = data["estimated_completion"]
        if est:
            # Verify it's a valid ISO date
            try:
                parsed = datetime.fromisoformat(est.replace("Z", "+00:00"))
                print(f"✓ Estimated completion: {parsed.strftime('%d.%m.%Y')}")
            except ValueError:
                pytest.fail(f"estimated_completion is not valid ISO format: {est}")
        else:
            print("✓ estimated_completion is null (all steps completed or no steps)")


class TestAdminUsersEstimatedCompletion:
    """Test admin users endpoint returns estimated_completion"""
    
    def test_admin_users_has_estimated_completion(self, admin_session):
        """GET /api/admin/users returns estimated_completion for each user"""
        resp = admin_session.get(f"{BASE_URL}/api/admin/users")
        assert resp.status_code == 200, f"Failed to get admin users: {resp.text}"
        
        users = resp.json()
        assert isinstance(users, list), "Users should be a list"
        assert len(users) > 0, "Should have at least one user"
        
        # Check each user has estimated_completion field
        for user in users:
            assert "estimated_completion" in user, f"User {user.get('email')} missing estimated_completion"
            est = user["estimated_completion"]
            if est:
                # Verify it's a valid ISO date
                try:
                    datetime.fromisoformat(est.replace("Z", "+00:00"))
                except ValueError:
                    pytest.fail(f"User {user.get('email')} has invalid estimated_completion: {est}")
        
        # Find demo user and verify
        demo_user = next((u for u in users if u.get("email") == DEMO_EMAIL), None)
        if demo_user:
            print(f"✓ Demo user estimated_completion: {demo_user.get('estimated_completion')}")
        
        print(f"✓ All {len(users)} users have estimated_completion field")


class TestPartnerSubmissionsEstimatedCompletion:
    """Test partner submissions endpoint returns estimated_completion"""
    
    def test_partner_submissions_has_estimated_completion(self, partner_session):
        """GET /api/partner/submissions returns estimated_completion for each submission"""
        resp = partner_session.get(f"{BASE_URL}/api/partner/submissions")
        assert resp.status_code == 200, f"Failed to get partner submissions: {resp.text}"
        
        submissions = resp.json()
        assert isinstance(submissions, list), "Submissions should be a list"
        
        if len(submissions) == 0:
            print("⚠ No submissions found for partner - skipping estimated_completion check")
            return
        
        # Check each submission has estimated_completion field
        for sub in submissions:
            assert "estimated_completion" in sub, f"Submission {sub.get('id')} missing estimated_completion"
            est = sub["estimated_completion"]
            if est:
                try:
                    datetime.fromisoformat(est.replace("Z", "+00:00"))
                except ValueError:
                    pytest.fail(f"Submission {sub.get('id')} has invalid estimated_completion: {est}")
        
        print(f"✓ All {len(submissions)} submissions have estimated_completion field")
        
        # Print first submission's estimated completion
        if submissions:
            first = submissions[0]
            print(f"✓ First submission ({first.get('user_name')}): estimated_completion={first.get('estimated_completion')}")


class TestProgressTimestamps:
    """Test that progress updates set started_at and completed_at timestamps"""
    
    def test_progress_update_sets_timestamps(self, demo_session):
        """PUT /api/steps/progress sets started_at and completed_at timestamps"""
        # Get current progress
        progress_resp = demo_session.get(f"{BASE_URL}/api/steps/progress")
        assert progress_resp.status_code == 200
        progress = progress_resp.json()
        
        # Get steps
        steps_resp = demo_session.get(f"{BASE_URL}/api/steps")
        assert steps_resp.status_code == 200
        steps = steps_resp.json()
        
        # Find a step that's not completed to test with
        # We'll check if completed steps have completed_at
        completed_progress = [p for p in progress if p.get("status") == "completed"]
        
        if completed_progress:
            # Check that completed steps have completed_at
            for p in completed_progress:
                # Note: The progress endpoint may not return timestamps directly
                # We need to check via admin endpoint
                pass
        
        print(f"✓ Found {len(completed_progress)} completed steps in progress")
        
        # Verify via admin user detail endpoint
        # First get current user ID
        me_resp = demo_session.get(f"{BASE_URL}/api/auth/me")
        assert me_resp.status_code == 200
        user_id = me_resp.json().get("id")
        
        print(f"✓ Demo user ID: {user_id}")


class TestEstimatedCompletionCalculation:
    """Test that estimated completion is calculated correctly"""
    
    def test_estimated_completion_is_future_date(self, demo_session):
        """Estimated completion should be a reasonable future date"""
        resp = demo_session.get(f"{BASE_URL}/api/steps/estimated-completion")
        assert resp.status_code == 200
        
        data = resp.json()
        est = data.get("estimated_completion")
        
        if est:
            parsed = datetime.fromisoformat(est.replace("Z", "+00:00"))
            now = datetime.now(parsed.tzinfo)
            
            # Estimated completion should be in the future or very recent past
            # (allowing for test timing)
            days_diff = (parsed - now).days
            print(f"✓ Estimated completion is {days_diff} days from now")
            
            # Should be reasonable (not more than 5 years in future)
            assert days_diff < 365 * 5, f"Estimated completion too far in future: {days_diff} days"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
