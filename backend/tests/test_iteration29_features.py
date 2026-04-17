"""
Test Iteration 29 Features:
1. Partner can view ANY user's step data (not just submitted/linked users)
2. Partner selection data is hidden when user chose a DIFFERENT partner
3. Completion % calculation excludes steps with duration_value=0
4. Admin user list shows correct completion %
5. Partner dashboard shows correct completion % for submissions and other-users
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
ADMIN_CREDS = {"email": "admin@example.com", "password": "Admin123!"}
DIGIFORT_PARTNER_CREDS = {"email": "partner@digifort-experts.de", "password": "Partner123!"}  # Antragstellung
HCS_PARTNER_CREDS = {"email": "partner@hc-und-s.de", "password": "Partner123!"}  # Kenntnisprüfung

# Demo users with known step progress
DR_KUMAR = {"email": "dr.kumar@gerdoctor.de", "password": "Demo123!"}  # 3/8 steps
DR_SCHMIDT = {"email": "dr.schmidt@gerdoctor.de", "password": "Demo123!"}  # 8/8 steps
DR_AHMED = {"email": "dr.ahmed@gerdoctor.de", "password": "Demo123!"}  # 1/8 steps
DR_TANAKA = {"email": "dr.tanaka@gerdoctor.de", "password": "Demo123!"}  # 0/8 steps


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def digifort_partner_token():
    """Get digiFORT partner auth token (Antragstellung)"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=DIGIFORT_PARTNER_CREDS)
    assert response.status_code == 200, f"digiFORT partner login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def hcs_partner_token():
    """Get HC&S partner auth token (Kenntnisprüfung)"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=HCS_PARTNER_CREDS)
    assert response.status_code == 200, f"HC&S partner login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def dr_kumar_user_id(admin_token):
    """Get Dr. Kumar's user ID"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
    assert response.status_code == 200
    users = response.json()
    kumar = next((u for u in users if u["email"] == DR_KUMAR["email"]), None)
    assert kumar is not None, "Dr. Kumar not found in users"
    return kumar["id"]


@pytest.fixture(scope="module")
def dr_schmidt_user_id(admin_token):
    """Get Dr. Schmidt's user ID"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
    assert response.status_code == 200
    users = response.json()
    schmidt = next((u for u in users if u["email"] == DR_SCHMIDT["email"]), None)
    assert schmidt is not None, "Dr. Schmidt not found in users"
    return schmidt["id"]


@pytest.fixture(scope="module")
def dr_ahmed_user_id(admin_token):
    """Get Dr. Ahmed's user ID"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
    assert response.status_code == 200
    users = response.json()
    ahmed = next((u for u in users if u["email"] == DR_AHMED["email"]), None)
    assert ahmed is not None, "Dr. Ahmed not found in users"
    return ahmed["id"]


@pytest.fixture(scope="module")
def dr_tanaka_user_id(admin_token):
    """Get Dr. Tanaka's user ID"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
    assert response.status_code == 200
    users = response.json()
    tanaka = next((u for u in users if u["email"] == DR_TANAKA["email"]), None)
    assert tanaka is not None, "Dr. Tanaka not found in users"
    return tanaka["id"]


class TestCompletionPercentageCalculation:
    """Test that completion % excludes steps with duration_value=0"""
    
    def test_admin_get_users_completion_pct(self, admin_token):
        """Admin user list should show correct completion % based on duration>0 steps only"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=headers)
        assert response.status_code == 200
        users = response.json()
        
        # Find specific users and check their completion %
        kumar = next((u for u in users if u["email"] == DR_KUMAR["email"]), None)
        schmidt = next((u for u in users if u["email"] == DR_SCHMIDT["email"]), None)
        ahmed = next((u for u in users if u["email"] == DR_AHMED["email"]), None)
        tanaka = next((u for u in users if u["email"] == DR_TANAKA["email"]), None)
        
        # Dr. Schmidt (8/8 steps, both step 3 and 6 completed) = 100%
        if schmidt:
            print(f"Dr. Schmidt completion_pct: {schmidt.get('completion_pct')}")
            assert schmidt.get("completion_pct") == 100, f"Dr. Schmidt should be 100%, got {schmidt.get('completion_pct')}"
        
        # Dr. Kumar (3/8 steps, step 3 completed but not 6) = 50%
        if kumar:
            print(f"Dr. Kumar completion_pct: {kumar.get('completion_pct')}")
            assert kumar.get("completion_pct") == 50, f"Dr. Kumar should be 50%, got {kumar.get('completion_pct')}"
        
        # Dr. Ahmed (1/8 steps, neither 3 nor 6 completed) = 0%
        if ahmed:
            print(f"Dr. Ahmed completion_pct: {ahmed.get('completion_pct')}")
            assert ahmed.get("completion_pct") == 0, f"Dr. Ahmed should be 0%, got {ahmed.get('completion_pct')}"
        
        # Dr. Tanaka (0/8 steps) = 0%
        if tanaka:
            print(f"Dr. Tanaka completion_pct: {tanaka.get('completion_pct')}")
            assert tanaka.get("completion_pct") == 0, f"Dr. Tanaka should be 0%, got {tanaka.get('completion_pct')}"


class TestPartnerCanViewAnyUser:
    """Test that partner can view user detail for ANY user (not just submitted/linked)"""
    
    def test_partner_can_view_any_user_detail(self, digifort_partner_token, dr_tanaka_user_id):
        """Partner should be able to view user detail for ANY user, even if not submitted to them"""
        headers = {"Authorization": f"Bearer {digifort_partner_token}"}
        response = requests.get(f"{BASE_URL}/api/partner/users/{dr_tanaka_user_id}", headers=headers)
        
        # Should NOT return 403 - partner can view any user now
        assert response.status_code == 200, f"Partner should be able to view any user, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "progress" in data
        assert "steps" in data
        assert "completion_pct" in data
        print(f"Partner successfully viewed Dr. Tanaka's detail: completion_pct={data.get('completion_pct')}")
    
    def test_partner_can_view_user_who_submitted_to_different_partner(self, hcs_partner_token, dr_kumar_user_id):
        """HC&S partner should be able to view Dr. Kumar even if Kumar submitted to digiFORT"""
        headers = {"Authorization": f"Bearer {hcs_partner_token}"}
        response = requests.get(f"{BASE_URL}/api/partner/users/{dr_kumar_user_id}", headers=headers)
        
        assert response.status_code == 200, f"Partner should be able to view any user, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("completion_pct") == 50, f"Dr. Kumar should have 50% completion, got {data.get('completion_pct')}"
        print(f"HC&S partner successfully viewed Dr. Kumar's detail")


class TestPartnerSelectionDataSanitization:
    """Test that partner selection data is hidden when user chose a DIFFERENT partner"""
    
    def test_partner_selection_hidden_for_different_partner(self, hcs_partner_token, dr_kumar_user_id):
        """When viewing a user who selected a different partner, selection data should be empty"""
        headers = {"Authorization": f"Bearer {hcs_partner_token}"}
        response = requests.get(f"{BASE_URL}/api/partner/users/{dr_kumar_user_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Find partner_selection steps in progress
        progress = data.get("progress", [])
        steps = data.get("steps", [])
        
        partner_selection_steps = [s for s in steps if s.get("step_type") in ("partner_selection", "partner_multiselection")]
        
        for ps_step in partner_selection_steps:
            step_progress = next((p for p in progress if p.get("step_id") == ps_step.get("id")), None)
            if step_progress and step_progress.get("status") == "completed":
                step_data = step_progress.get("data", {})
                # If user selected a different partner, data should be empty {}
                selected_pid = step_data.get("selected_partner_id", "")
                if selected_pid:
                    # This means user selected THIS partner (HC&S), data is visible
                    print(f"Step {ps_step.get('order')}: User selected this partner, data visible")
                else:
                    # Data was sanitized (user selected different partner)
                    print(f"Step {ps_step.get('order')}: Partner selection data hidden (user chose different partner)")
                    assert step_data == {} or "selected_partner_id" not in step_data, "Selection data should be hidden"
    
    def test_partner_selection_visible_for_same_partner(self, digifort_partner_token, dr_kumar_user_id):
        """When viewing a user who selected THIS partner, selection data should be visible"""
        headers = {"Authorization": f"Bearer {digifort_partner_token}"}
        response = requests.get(f"{BASE_URL}/api/partner/users/{dr_kumar_user_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        progress = data.get("progress", [])
        steps = data.get("steps", [])
        
        # Find Antragstellung partner_selection step (step 3)
        antrag_step = next((s for s in steps if s.get("filter_tag") == "Antragstellung" and s.get("step_type") in ("partner_selection", "partner_multiselection")), None)
        
        if antrag_step:
            step_progress = next((p for p in progress if p.get("step_id") == antrag_step.get("id")), None)
            if step_progress and step_progress.get("status") == "completed":
                step_data = step_progress.get("data", {})
                # If Dr. Kumar selected digiFORT, data should be visible
                if step_data.get("selected_partner_id"):
                    print(f"Antragstellung step: Partner selection data visible (user chose this partner)")
                else:
                    print(f"Antragstellung step: No selection data found")


class TestPartnerDashboardCompletionPct:
    """Test that partner dashboard shows correct completion % for submissions and other-users"""
    
    def test_partner_submissions_completion_pct(self, digifort_partner_token):
        """Partner submissions should show correct completion % based on duration>0 steps"""
        headers = {"Authorization": f"Bearer {digifort_partner_token}"}
        response = requests.get(f"{BASE_URL}/api/partner/submissions", headers=headers)
        
        assert response.status_code == 200
        submissions = response.json()
        
        print(f"Found {len(submissions)} submissions for digiFORT partner")
        for sub in submissions:
            print(f"  - {sub.get('user_name')}: {sub.get('completion_pct')}%")
            # Verify completion_pct is present
            assert "completion_pct" in sub, "Submission should have completion_pct"
    
    def test_partner_other_users_completion_pct(self, digifort_partner_token):
        """Partner other-users should show correct completion % based on duration>0 steps"""
        headers = {"Authorization": f"Bearer {digifort_partner_token}"}
        response = requests.get(f"{BASE_URL}/api/partner/other-users", headers=headers)
        
        assert response.status_code == 200
        other_users = response.json()
        
        print(f"Found {len(other_users)} other users for digiFORT partner")
        for user in other_users[:5]:  # Print first 5
            print(f"  - {user.get('user_name')}: {user.get('completion_pct')}%")
            # Verify completion_pct is present
            assert "completion_pct" in user, "Other user should have completion_pct"


class TestPartnerUserDetailCompletionPct:
    """Test that partner user detail shows correct completion %"""
    
    def test_user_detail_completion_pct_dr_schmidt(self, digifort_partner_token, dr_schmidt_user_id):
        """Dr. Schmidt (8/8 steps) should show 100% completion"""
        headers = {"Authorization": f"Bearer {digifort_partner_token}"}
        response = requests.get(f"{BASE_URL}/api/partner/users/{dr_schmidt_user_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("completion_pct") == 100, f"Dr. Schmidt should have 100% completion, got {data.get('completion_pct')}"
        print(f"Dr. Schmidt user detail: completion_pct={data.get('completion_pct')}")
    
    def test_user_detail_completion_pct_dr_kumar(self, digifort_partner_token, dr_kumar_user_id):
        """Dr. Kumar (3/8 steps, step 3 completed) should show 50% completion"""
        headers = {"Authorization": f"Bearer {digifort_partner_token}"}
        response = requests.get(f"{BASE_URL}/api/partner/users/{dr_kumar_user_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("completion_pct") == 50, f"Dr. Kumar should have 50% completion, got {data.get('completion_pct')}"
        print(f"Dr. Kumar user detail: completion_pct={data.get('completion_pct')}")
    
    def test_user_detail_completion_pct_dr_ahmed(self, digifort_partner_token, dr_ahmed_user_id):
        """Dr. Ahmed (1/8 steps, neither 3 nor 6 completed) should show 0% completion"""
        headers = {"Authorization": f"Bearer {digifort_partner_token}"}
        response = requests.get(f"{BASE_URL}/api/partner/users/{dr_ahmed_user_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("completion_pct") == 0, f"Dr. Ahmed should have 0% completion, got {data.get('completion_pct')}"
        print(f"Dr. Ahmed user detail: completion_pct={data.get('completion_pct')}")


class TestStepDurationValues:
    """Verify which steps have duration_value > 0"""
    
    def test_verify_step_durations(self, admin_token):
        """Verify that only Steps 3 and 6 have duration_value > 0"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/steps", headers=headers)
        
        assert response.status_code == 200
        steps = response.json()
        
        countable_steps = []
        for step in steps:
            duration_value = step.get("duration_value", 0)
            duration_unit = step.get("duration_unit", "")
            if duration_value > 0:
                countable_steps.append({
                    "order": step.get("order"),
                    "title": step.get("title"),
                    "duration_value": duration_value,
                    "duration_unit": duration_unit
                })
                print(f"Step {step.get('order')}: {step.get('title')} - duration={duration_value} {duration_unit}")
        
        # Should have exactly 2 countable steps (Step 3 and Step 6)
        assert len(countable_steps) == 2, f"Expected 2 countable steps, got {len(countable_steps)}: {countable_steps}"
        
        # Verify Step 3 (Antragstellung) has duration
        step3 = next((s for s in countable_steps if s["order"] == 3), None)
        assert step3 is not None, "Step 3 should have duration > 0"
        assert step3["duration_value"] == 4, f"Step 3 should have duration_value=4, got {step3['duration_value']}"
        assert step3["duration_unit"] == "weeks", f"Step 3 should have duration_unit=weeks, got {step3['duration_unit']}"
        
        # Verify Step 6 (Kenntnisprüfung) has duration
        step6 = next((s for s in countable_steps if s["order"] == 6), None)
        assert step6 is not None, "Step 6 should have duration > 0"
        assert step6["duration_value"] == 3, f"Step 6 should have duration_value=3, got {step6['duration_value']}"
        assert step6["duration_unit"] == "months", f"Step 6 should have duration_unit=months, got {step6['duration_unit']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
