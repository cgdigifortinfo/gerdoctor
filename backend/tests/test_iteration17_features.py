"""
Test Iteration 17 Features:
1. DUPLICATE FIX: Backend submit endpoint upserts - submitting to same partner twice should update not create duplicate
2. STEP DATA DISPLAY: Partner detail endpoint returns step data with field definitions for label display
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
PARTNER_EMAIL = "partner@example.com"
PARTNER_PASSWORD = "Partner123!"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Demo123!"

# Known ILS partner ID (partner@example.com is linked to this)
ILS_PARTNER_ID = "69de3c12faf9cbab373b72b9"

# Known user with submission to ILS partner (Chris)
CHRIS_USER_ID = "69df40be8f79a5790086315f"


class TestDuplicateSubmissionFix:
    """Test that submitting to same partner twice updates instead of creating duplicate"""
    
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
    
    def test_submit_to_partner_creates_submission(self, demo_session, partner_session):
        """First submission to partner creates a new submission"""
        # Get demo user ID
        me_resp = demo_session.get(f"{BASE_URL}/api/auth/me")
        assert me_resp.status_code == 200
        demo_user_id = me_resp.json()["id"]
        
        # Submit to ILS partner
        submit_resp = demo_session.post(
            f"{BASE_URL}/api/partners/submit",
            json={
                "partner_id": ILS_PARTNER_ID,
                "data": {"test_field": "first_submission", "timestamp": str(time.time())}
            }
        )
        assert submit_resp.status_code == 200, f"Submit failed: {submit_resp.text}"
        result = submit_resp.json()
        assert "submission_id" in result, "Response should contain submission_id"
        print(f"SUCCESS: First submission created with ID: {result.get('submission_id')}")
        
        # Verify submission appears in partner's list
        subs_resp = partner_session.get(f"{BASE_URL}/api/partner/submissions")
        assert subs_resp.status_code == 200
        submissions = subs_resp.json()
        
        # Find demo user's submission
        demo_submissions = [s for s in submissions if s.get("user_id") == demo_user_id]
        assert len(demo_submissions) >= 1, "Demo user should have at least 1 submission"
        print(f"SUCCESS: Demo user has {len(demo_submissions)} submission(s) to ILS partner")
    
    def test_submit_twice_to_same_partner_updates_not_duplicates(self, demo_session, partner_session):
        """Submitting twice to same partner should update existing, not create duplicate"""
        # Get demo user ID
        me_resp = demo_session.get(f"{BASE_URL}/api/auth/me")
        assert me_resp.status_code == 200
        demo_user_id = me_resp.json()["id"]
        
        # Get initial submission count
        subs_resp_before = partner_session.get(f"{BASE_URL}/api/partner/submissions")
        assert subs_resp_before.status_code == 200
        submissions_before = subs_resp_before.json()
        demo_subs_before = [s for s in submissions_before if s.get("user_id") == demo_user_id]
        count_before = len(demo_subs_before)
        print(f"Before second submit: {count_before} submission(s) from demo user")
        
        # Submit again to same partner with different data
        submit_resp = demo_session.post(
            f"{BASE_URL}/api/partners/submit",
            json={
                "partner_id": ILS_PARTNER_ID,
                "data": {"test_field": "second_submission", "timestamp": str(time.time())}
            }
        )
        assert submit_resp.status_code == 200, f"Second submit failed: {submit_resp.text}"
        result = submit_resp.json()
        # Should say "updated" not "created"
        assert "Submission" in result.get("message", ""), f"Unexpected message: {result}"
        print(f"SUCCESS: Second submission response: {result.get('message')}")
        
        # Verify NO duplicate - count should be same
        subs_resp_after = partner_session.get(f"{BASE_URL}/api/partner/submissions")
        assert subs_resp_after.status_code == 200
        submissions_after = subs_resp_after.json()
        demo_subs_after = [s for s in submissions_after if s.get("user_id") == demo_user_id]
        count_after = len(demo_subs_after)
        print(f"After second submit: {count_after} submission(s) from demo user")
        
        # CRITICAL: Count should NOT increase (upsert behavior)
        assert count_after == count_before, f"DUPLICATE BUG: Count increased from {count_before} to {count_after}"
        print(f"SUCCESS: No duplicate created - count stayed at {count_after}")
    
    def test_partner_submission_list_shows_each_user_once(self, partner_session):
        """Partner submission list should show each user only ONCE (no duplicates)"""
        subs_resp = partner_session.get(f"{BASE_URL}/api/partner/submissions")
        assert subs_resp.status_code == 200
        submissions = subs_resp.json()
        
        # Check for duplicates by user_id
        user_ids = [s.get("user_id") for s in submissions]
        unique_user_ids = set(user_ids)
        
        print(f"Total submissions: {len(submissions)}")
        print(f"Unique users: {len(unique_user_ids)}")
        
        # CRITICAL: No duplicates
        assert len(user_ids) == len(unique_user_ids), f"DUPLICATE BUG: Found duplicate user_ids. Total: {len(user_ids)}, Unique: {len(unique_user_ids)}"
        print(f"SUCCESS: No duplicate users in submission list")
        
        # List all submissions
        for sub in submissions:
            print(f"  - {sub.get('user_name')} ({sub.get('user_email')})")


class TestStepDataDisplay:
    """Test that partner user detail endpoint returns step data with field definitions"""
    
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
    
    def test_user_detail_returns_steps_with_fields(self, partner_session):
        """Partner user detail should return steps with field definitions for label display"""
        response = partner_session.get(f"{BASE_URL}/api/partner/users/{CHRIS_USER_ID}")
        assert response.status_code == 200, f"Failed to get user detail: {response.text}"
        
        data = response.json()
        steps = data.get("steps", [])
        progress = data.get("progress", [])
        
        assert len(steps) > 0, "Should have steps"
        print(f"User has {len(steps)} steps")
        
        # Check that steps have field definitions
        for step in steps:
            step_order = step.get("order")
            step_title = step.get("title")
            step_type = step.get("step_type")
            fields = step.get("fields", [])
            
            print(f"\nStep {step_order}: {step_title} ({step_type})")
            print(f"  Fields: {len(fields)}")
            
            # For form and partner_selection steps, should have fields
            if step_type in ["form", "partner_selection"]:
                # Check field structure
                for field in fields:
                    assert "name" in field, f"Field should have 'name'"
                    assert "label" in field, f"Field should have 'label'"
                    print(f"    - {field.get('name')}: {field.get('label')}")
    
    def test_user_detail_returns_progress_with_data(self, partner_session):
        """Partner user detail should return progress with step data"""
        response = partner_session.get(f"{BASE_URL}/api/partner/users/{CHRIS_USER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        steps = data.get("steps", [])
        progress = data.get("progress", [])
        
        # Create progress map
        progress_map = {p.get("step_id"): p for p in progress}
        
        print(f"\nProgress data for each step:")
        steps_with_data = 0
        for step in steps:
            step_id = step.get("id")
            step_order = step.get("order")
            step_title = step.get("title")
            
            prog = progress_map.get(step_id, {})
            status = prog.get("status", "pending")
            step_data = prog.get("data", {})
            
            print(f"\nStep {step_order}: {step_title}")
            print(f"  Status: {status}")
            print(f"  Data keys: {list(step_data.keys()) if step_data else 'None'}")
            
            if step_data and len(step_data) > 0:
                steps_with_data += 1
                for key, value in step_data.items():
                    if key != "skipped":
                        print(f"    {key}: {value}")
        
        print(f"\nSteps with data: {steps_with_data}")
        # Chris should have data in some steps (partner selection steps have selected_partner_id)
        assert steps_with_data > 0, "Chris should have data in at least some steps"
        print(f"SUCCESS: User has data in {steps_with_data} steps")
    
    def test_partner_selection_step_has_selected_partner_data(self, partner_session):
        """Partner selection steps should have selected_partner_id in data"""
        response = partner_session.get(f"{BASE_URL}/api/partner/users/{CHRIS_USER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        steps = data.get("steps", [])
        progress = data.get("progress", [])
        
        # Create progress map
        progress_map = {p.get("step_id"): p for p in progress}
        
        # Find partner_selection steps
        partner_selection_steps = [s for s in steps if s.get("step_type") == "partner_selection"]
        print(f"Found {len(partner_selection_steps)} partner_selection steps")
        
        steps_with_partner_data = 0
        for step in partner_selection_steps:
            step_id = step.get("id")
            step_order = step.get("order")
            step_title = step.get("title")
            
            prog = progress_map.get(step_id, {})
            step_data = prog.get("data", {})
            
            print(f"\nStep {step_order}: {step_title}")
            print(f"  Data: {step_data}")
            
            if "selected_partner_id" in step_data:
                steps_with_partner_data += 1
                print(f"  SUCCESS: Has selected_partner_id: {step_data.get('selected_partner_id')}")
        
        # At least one partner selection step should have data (Chris submitted to ILS)
        assert steps_with_partner_data > 0, "At least one partner_selection step should have selected_partner_id"
        print(f"\nSUCCESS: {steps_with_partner_data} partner_selection steps have selected_partner_id")


class TestPartnerCompleteButton:
    """Test that partner can complete steps for users"""
    
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
    
    def test_partner_can_complete_step(self, partner_session):
        """Partner can mark a step as completed for a user who submitted to them"""
        # Get user detail
        detail_resp = partner_session.get(f"{BASE_URL}/api/partner/users/{CHRIS_USER_ID}")
        assert detail_resp.status_code == 200
        
        data = detail_resp.json()
        steps = data.get("steps", [])
        progress = data.get("progress", [])
        
        # Create progress map
        progress_map = {p.get("step_id"): p for p in progress}
        
        # Find a non-completed step
        non_completed_step = None
        for step in steps:
            step_id = step.get("id")
            prog = progress_map.get(step_id, {})
            if prog.get("status") != "completed":
                non_completed_step = step
                break
        
        if non_completed_step:
            step_id = non_completed_step.get("id")
            step_order = non_completed_step.get("order")
            print(f"Found non-completed step {step_order}: {non_completed_step.get('title')}")
            
            # Complete the step
            update_resp = partner_session.put(
                f"{BASE_URL}/api/partner/users/{CHRIS_USER_ID}/progress",
                json={
                    "step_id": step_id,
                    "status": "completed",
                    "data": {}
                }
            )
            assert update_resp.status_code == 200, f"Failed to complete step: {update_resp.text}"
            print(f"SUCCESS: Partner completed step {step_order}")
            
            # Verify step is now completed
            verify_resp = partner_session.get(f"{BASE_URL}/api/partner/users/{CHRIS_USER_ID}")
            assert verify_resp.status_code == 200
            verify_data = verify_resp.json()
            verify_progress = {p.get("step_id"): p for p in verify_data.get("progress", [])}
            
            updated_status = verify_progress.get(step_id, {}).get("status")
            assert updated_status == "completed", f"Step should be completed, got {updated_status}"
            print(f"SUCCESS: Step {step_order} verified as completed")
        else:
            print("All steps already completed - skipping test")
            pytest.skip("All steps already completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
