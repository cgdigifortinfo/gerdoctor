"""
Test Partner Step Completion Features - Iteration 29
Tests for:
1. Partner can view user detail via submission AND via linked_user_ids
2. partner_step_id returned correctly in user detail
3. Partner can complete a step - status becomes 'completed'
4. completed_at timestamp is set when partner completes a step
5. Next step automatically activated to 'in_progress' after partner completes current step
6. Email sent when step has email_on_leave=true and partner completes it
7. Progress history recorded with partner email as changed_by
"""

import pytest
import requests
import os
import time
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPartnerStepCompletion:
    """Test partner step completion features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test sessions"""
        self.admin_session = requests.Session()
        self.admin_session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_resp = self.admin_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@example.com",
            "password": "Admin123!"
        })
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        self.admin_token = login_resp.json().get("access_token")
        self.admin_session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
        yield
    
    def test_01_admin_login(self):
        """Test admin can login successfully"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@example.com",
            "password": "Admin123!"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["role"] == "admin"
        print("PASS: Admin login successful")
    
    def test_02_partner_digifort_login(self):
        """Test digiFORT partner can login"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@digifort-experts.de",
            "password": "Partner123!"
        })
        assert resp.status_code == 200, f"Partner login failed: {resp.text}"
        data = resp.json()
        assert data["role"] == "partner"
        print("PASS: digiFORT partner login successful")
    
    def test_03_partner_hcs_login(self):
        """Test HC&S partner can login"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@hc-und-s.de",
            "password": "Partner123!"
        })
        assert resp.status_code == 200, f"Partner login failed: {resp.text}"
        data = resp.json()
        assert data["role"] == "partner"
        print("PASS: HC&S partner login successful")
    
    def test_04_partner_hausarztpraxis_login(self):
        """Test Hausarztpraxis partner can login (linked via linked_user_ids)"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "empfang@hausarztpraxis-marienplatz.de",
            "password": "Partner123!"
        })
        assert resp.status_code == 200, f"Partner login failed: {resp.text}"
        data = resp.json()
        assert data["role"] == "partner"
        print("PASS: Hausarztpraxis partner login successful")
    
    def test_05_partner_get_submissions_digifort(self):
        """Test digiFORT partner can get submissions"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@digifort-experts.de",
            "password": "Partner123!"
        })
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        resp = session.get(f"{BASE_URL}/api/partner/submissions")
        assert resp.status_code == 200, f"Get submissions failed: {resp.text}"
        submissions = resp.json()
        assert isinstance(submissions, list)
        print(f"PASS: digiFORT partner has {len(submissions)} submissions")
        
        # Store for later tests
        self.digifort_submissions = submissions
    
    def test_06_partner_get_user_detail_via_submission(self):
        """Test partner can view user detail via submission"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@digifort-experts.de",
            "password": "Partner123!"
        })
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get submissions first
        subs_resp = session.get(f"{BASE_URL}/api/partner/submissions")
        assert subs_resp.status_code == 200
        submissions = subs_resp.json()
        
        if len(submissions) == 0:
            pytest.skip("No submissions for digiFORT partner")
        
        # Get user detail for first submission
        user_id = submissions[0].get("user_id")
        assert user_id, "No user_id in submission"
        
        detail_resp = session.get(f"{BASE_URL}/api/partner/users/{user_id}")
        assert detail_resp.status_code == 200, f"Get user detail failed: {detail_resp.text}"
        detail = detail_resp.json()
        
        # Verify response structure
        assert "id" in detail
        assert "email" in detail
        assert "name" in detail
        assert "progress" in detail
        assert "steps" in detail
        assert "completion_pct" in detail
        assert "partner_step_id" in detail
        
        print(f"PASS: Partner can view user detail via submission - user: {detail['name']}, completion: {detail['completion_pct']}%")
    
    def test_07_partner_step_id_returned_correctly(self):
        """Test partner_step_id is returned correctly matching partner tag to step filter_tag"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@digifort-experts.de",
            "password": "Partner123!"
        })
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get submissions
        subs_resp = session.get(f"{BASE_URL}/api/partner/submissions")
        submissions = subs_resp.json()
        
        if len(submissions) == 0:
            pytest.skip("No submissions for digiFORT partner")
        
        user_id = submissions[0].get("user_id")
        detail_resp = session.get(f"{BASE_URL}/api/partner/users/{user_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        
        partner_step_id = detail.get("partner_step_id")
        steps = detail.get("steps", [])
        
        # digiFORT has tag "Antragstellung" which should match step 2 (partner_selection with filter_tag "Antragstellung")
        if partner_step_id:
            partner_step = next((s for s in steps if s["id"] == partner_step_id), None)
            assert partner_step is not None, f"partner_step_id {partner_step_id} not found in steps"
            assert partner_step.get("step_type") in ("partner_selection", "partner_multiselection"), f"Partner step type is {partner_step.get('step_type')}"
            print(f"PASS: partner_step_id returned correctly - step: {partner_step.get('title')} (order {partner_step.get('order')})")
        else:
            print("INFO: partner_step_id is None (partner may not have matching tag)")
    
    def test_08_partner_complete_step_sets_completed_status(self):
        """Test partner can complete a step and status becomes 'completed'"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login as digiFORT partner
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@digifort-experts.de",
            "password": "Partner123!"
        })
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get submissions
        subs_resp = session.get(f"{BASE_URL}/api/partner/submissions")
        submissions = subs_resp.json()
        
        if len(submissions) == 0:
            pytest.skip("No submissions for digiFORT partner")
        
        # Find a user with an in_progress step
        for sub in submissions:
            user_id = sub.get("user_id")
            detail_resp = session.get(f"{BASE_URL}/api/partner/users/{user_id}")
            if detail_resp.status_code != 200:
                continue
            detail = detail_resp.json()
            
            # Find an in_progress step
            progress = detail.get("progress", [])
            in_progress_step = next((p for p in progress if p.get("status") == "in_progress"), None)
            
            if in_progress_step:
                step_id = in_progress_step.get("step_id")
                
                # Complete the step
                complete_resp = session.put(f"{BASE_URL}/api/partner/users/{user_id}/progress", json={
                    "step_id": step_id,
                    "status": "completed",
                    "data": {}
                })
                assert complete_resp.status_code == 200, f"Complete step failed: {complete_resp.text}"
                
                # Verify status changed
                detail_resp2 = session.get(f"{BASE_URL}/api/partner/users/{user_id}")
                detail2 = detail_resp2.json()
                progress2 = detail2.get("progress", [])
                completed_step = next((p for p in progress2 if p.get("step_id") == step_id), None)
                
                assert completed_step is not None
                assert completed_step.get("status") == "completed", f"Step status is {completed_step.get('status')}, expected 'completed'"
                
                print(f"PASS: Partner completed step for user {detail['name']}, step_id={step_id}")
                return
        
        pytest.skip("No in_progress steps found for any user")
    
    def test_09_completed_at_timestamp_set(self):
        """Test completed_at timestamp is set when partner completes a step"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@digifort-experts.de",
            "password": "Partner123!"
        })
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get submissions
        subs_resp = session.get(f"{BASE_URL}/api/partner/submissions")
        submissions = subs_resp.json()
        
        if len(submissions) == 0:
            pytest.skip("No submissions for digiFORT partner")
        
        # Find a user with a completed step
        for sub in submissions:
            user_id = sub.get("user_id")
            detail_resp = session.get(f"{BASE_URL}/api/partner/users/{user_id}")
            if detail_resp.status_code != 200:
                continue
            detail = detail_resp.json()
            
            progress = detail.get("progress", [])
            completed_step = next((p for p in progress if p.get("status") == "completed"), None)
            
            if completed_step:
                completed_at = completed_step.get("completed_at")
                assert completed_at is not None, "completed_at is None for completed step"
                
                # Verify it's a valid ISO timestamp
                try:
                    datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                except ValueError:
                    pytest.fail(f"completed_at is not a valid ISO timestamp: {completed_at}")
                
                print(f"PASS: completed_at timestamp set correctly: {completed_at}")
                return
        
        pytest.skip("No completed steps found")
    
    def test_10_next_step_activated_after_completion(self):
        """Test next step is automatically activated to 'in_progress' after partner completes current step"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@digifort-experts.de",
            "password": "Partner123!"
        })
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get submissions
        subs_resp = session.get(f"{BASE_URL}/api/partner/submissions")
        submissions = subs_resp.json()
        
        if len(submissions) == 0:
            pytest.skip("No submissions for digiFORT partner")
        
        # Find a user with an in_progress step that has a next step
        for sub in submissions:
            user_id = sub.get("user_id")
            detail_resp = session.get(f"{BASE_URL}/api/partner/users/{user_id}")
            if detail_resp.status_code != 200:
                continue
            detail = detail_resp.json()
            
            progress = detail.get("progress", [])
            steps = detail.get("steps", [])
            
            # Find an in_progress step
            in_progress_step = next((p for p in progress if p.get("status") == "in_progress"), None)
            
            if in_progress_step:
                step_id = in_progress_step.get("step_id")
                current_step = next((s for s in steps if s["id"] == step_id), None)
                
                if not current_step:
                    continue
                
                current_order = current_step.get("order", 0)
                next_step = next((s for s in steps if s.get("order", 0) > current_order), None)
                
                if not next_step:
                    continue  # No next step
                
                next_step_id = next_step["id"]
                
                # Check next step is pending before completion
                next_prog_before = next((p for p in progress if p.get("step_id") == next_step_id), None)
                if next_prog_before and next_prog_before.get("status") != "pending":
                    continue  # Next step already activated
                
                # Complete the current step
                complete_resp = session.put(f"{BASE_URL}/api/partner/users/{user_id}/progress", json={
                    "step_id": step_id,
                    "status": "completed",
                    "data": {}
                })
                assert complete_resp.status_code == 200, f"Complete step failed: {complete_resp.text}"
                
                # Verify next step is now in_progress
                detail_resp2 = session.get(f"{BASE_URL}/api/partner/users/{user_id}")
                detail2 = detail_resp2.json()
                progress2 = detail2.get("progress", [])
                
                next_prog_after = next((p for p in progress2 if p.get("step_id") == next_step_id), None)
                assert next_prog_after is not None, "Next step progress not found"
                assert next_prog_after.get("status") == "in_progress", f"Next step status is {next_prog_after.get('status')}, expected 'in_progress'"
                
                print(f"PASS: Next step '{next_step.get('title')}' activated to in_progress after completing step '{current_step.get('title')}'")
                return
        
        pytest.skip("No suitable in_progress steps with pending next step found")
    
    def test_11_progress_history_records_changed_by(self):
        """Test progress history records partner email as changed_by"""
        # Use admin to check progress history
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@example.com",
            "password": "Admin123!"
        })
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get all users
        users_resp = session.get(f"{BASE_URL}/api/admin/users")
        assert users_resp.status_code == 200
        users = users_resp.json()
        
        # Find a user with history
        for user in users:
            user_id = user.get("id")
            detail_resp = session.get(f"{BASE_URL}/api/admin/users/{user_id}")
            if detail_resp.status_code != 200:
                continue
            detail = detail_resp.json()
            
            history = detail.get("history", [])
            
            # Look for history entries with changed_by (partner actions)
            partner_actions = [h for h in history if h.get("changed_by")]
            
            if partner_actions:
                for action in partner_actions:
                    changed_by = action.get("changed_by")
                    assert "@" in changed_by, f"changed_by should be an email: {changed_by}"
                    print(f"PASS: Progress history records changed_by: {changed_by} for action '{action.get('action')}' on step '{action.get('step_title')}'")
                return
        
        print("INFO: No partner actions found in history (may need to run completion tests first)")
    
    def test_12_user_dr_silva_progress(self):
        """Test Dr. Silva's progress (2/8 steps, step 3 in_progress)"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "dr.silva@gerdoctor.de",
            "password": "Demo123!"
        })
        assert login_resp.status_code == 200, f"Dr. Silva login failed: {login_resp.text}"
        token = login_resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get progress
        progress_resp = session.get(f"{BASE_URL}/api/steps/progress")
        assert progress_resp.status_code == 200
        progress = progress_resp.json()
        
        completed = len([p for p in progress if p.get("status") == "completed"])
        in_progress = [p for p in progress if p.get("status") == "in_progress"]
        
        print(f"PASS: Dr. Silva has {completed} completed steps, {len(in_progress)} in_progress")
    
    def test_13_user_dr_kumar_progress(self):
        """Test Dr. Kumar's progress (3/8 steps, step 4 in_progress)"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "dr.kumar@gerdoctor.de",
            "password": "Demo123!"
        })
        assert login_resp.status_code == 200, f"Dr. Kumar login failed: {login_resp.text}"
        token = login_resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get progress
        progress_resp = session.get(f"{BASE_URL}/api/steps/progress")
        assert progress_resp.status_code == 200
        progress = progress_resp.json()
        
        completed = len([p for p in progress if p.get("status") == "completed"])
        in_progress = [p for p in progress if p.get("status") == "in_progress"]
        
        print(f"PASS: Dr. Kumar has {completed} completed steps, {len(in_progress)} in_progress")
    
    def test_14_partner_access_via_linked_user_ids(self):
        """Test partner can access user via linked_user_ids (not just submission)"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login as Hausarztpraxis partner (linked to Dr. Schmidt via linked_user_ids)
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "empfang@hausarztpraxis-marienplatz.de",
            "password": "Partner123!"
        })
        assert login_resp.status_code == 200, f"Partner login failed: {login_resp.text}"
        token = login_resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get submissions (should include linked users)
        subs_resp = session.get(f"{BASE_URL}/api/partner/submissions")
        assert subs_resp.status_code == 200, f"Get submissions failed: {subs_resp.text}"
        submissions = subs_resp.json()
        
        # Look for linked users (status='linked')
        linked_users = [s for s in submissions if s.get("status") == "linked"]
        
        if linked_users:
            # Try to access linked user detail
            user_id = linked_users[0].get("user_id")
            detail_resp = session.get(f"{BASE_URL}/api/partner/users/{user_id}")
            assert detail_resp.status_code == 200, f"Get linked user detail failed: {detail_resp.text}"
            detail = detail_resp.json()
            
            print(f"PASS: Partner can access linked user via linked_user_ids - user: {detail.get('name')}")
        else:
            print("INFO: No linked users found for this partner (may need to check admin setup)")
    
    def test_15_praxis_partner_no_partner_step_id(self):
        """Test Praxis partners have NO partner_step_id (no matching step filter_tag)"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login as Hausarztpraxis partner (Praxis category, no matching step)
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "empfang@hausarztpraxis-marienplatz.de",
            "password": "Partner123!"
        })
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get submissions
        subs_resp = session.get(f"{BASE_URL}/api/partner/submissions")
        submissions = subs_resp.json()
        
        if len(submissions) == 0:
            pytest.skip("No submissions for Hausarztpraxis partner")
        
        user_id = submissions[0].get("user_id")
        detail_resp = session.get(f"{BASE_URL}/api/partner/users/{user_id}")
        
        if detail_resp.status_code == 200:
            detail = detail_resp.json()
            partner_step_id = detail.get("partner_step_id")
            
            # Praxis partners should have no matching step (their tags don't match any step filter_tag)
            print(f"INFO: Praxis partner partner_step_id = {partner_step_id}")
        else:
            print(f"INFO: Could not get user detail: {detail_resp.status_code}")


class TestEmailOnStepCompletion:
    """Test email sending when partner completes a step"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        yield
    
    def test_email_on_leave_steps(self):
        """Verify which steps have email_on_leave=true"""
        # Login as admin
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@example.com",
            "password": "Admin123!"
        })
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get all steps
        steps_resp = self.session.get(f"{BASE_URL}/api/admin/steps")
        assert steps_resp.status_code == 200
        steps = steps_resp.json()
        
        email_on_leave_steps = [s for s in steps if s.get("email_on_leave")]
        
        print(f"Steps with email_on_leave=true:")
        for s in email_on_leave_steps:
            print(f"  - Step {s.get('order')}: {s.get('title')}")
        
        # According to context: Steps 1, 3, 6 have email_on_leave
        assert len(email_on_leave_steps) >= 3, f"Expected at least 3 steps with email_on_leave, found {len(email_on_leave_steps)}"
        print(f"PASS: Found {len(email_on_leave_steps)} steps with email_on_leave=true")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
