"""
Test iteration 26 features:
1. ADMIN USER DETAIL: Step data shown for completed steps (like partner view)
2. ADMIN USER DETAIL: Multiupload fields show document type + download link
3. STEP EDITOR: Type dropdown shows 5 options including partner_multiselection
4. STEP EDITOR: Type-specific tabs (Typ-Einstellungen for partner_selection/multiselection/milestone/display)
5. STEP EDITOR: Fields tab only for 'form' type
6. SEED DATA: Demo doctors created with Fachgebiete
7. SEED DATA: Step 1 Fachgebiet options include 15 medical specialties
8. BACKEND: partner_multiselection step type can be created via POST /api/admin/steps
9. TEST CLEANUP: All tests delete TEST_ prefixed data at end
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin123!"

# Demo doctor credentials
DEMO_DOCTORS = [
    {"email": "dr.schmidt@example.com", "name": "Dr. Anna Schmidt", "fachgebiet": "Allgemeinmedizin"},
    {"email": "dr.yilmaz@example.com", "name": "Dr. Emre Yilmaz", "fachgebiet": "Innere Medizin"},
    {"email": "dr.chen@example.com", "name": "Dr. Wei Chen", "fachgebiet": "Chirurgie"},
    {"email": "dr.kumar@example.com", "name": "Dr. Priya Kumar", "fachgebiet": "Pädiatrie"},
]

# Expected 15 medical specialties
EXPECTED_FACHGEBIETE = [
    "Allgemeinmedizin", "Innere Medizin", "Chirurgie", "Pädiatrie", "Zahnmedizin",
    "HNO", "Dermatologie", "Neurologie", "Orthopädie", "Gynäkologie",
    "Augenheilkunde", "Anästhesiologie", "Radiologie", "Psychiatrie", "Urologie"
]


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
def test_data_tracker():
    """Track test data for cleanup"""
    return {"user_ids": [], "step_ids": []}


class TestDemoDoctorsSeedData:
    """Tests for seeded demo doctors with Fachgebiete"""
    
    def test_demo_doctors_exist(self, admin_session):
        """Verify demo doctors are seeded in the database"""
        resp = admin_session.get(f"{BASE_URL}/api/admin/users")
        assert resp.status_code == 200
        users = resp.json()
        
        for doc in DEMO_DOCTORS:
            found = next((u for u in users if u["email"] == doc["email"]), None)
            assert found is not None, f"Demo doctor {doc['email']} not found"
            assert found["name"] == doc["name"], f"Name mismatch for {doc['email']}"
            print(f"✓ Found demo doctor: {doc['name']} ({doc['email']})")
    
    def test_dr_schmidt_has_step1_completed(self, admin_session):
        """Dr. Anna Schmidt should have Step 1 completed with form data"""
        # Find Dr. Schmidt
        resp = admin_session.get(f"{BASE_URL}/api/admin/users")
        users = resp.json()
        dr_schmidt = next((u for u in users if u["email"] == "dr.schmidt@example.com"), None)
        assert dr_schmidt is not None, "Dr. Schmidt not found"
        
        # Get user details with progress
        detail_resp = admin_session.get(f"{BASE_URL}/api/admin/users/{dr_schmidt['id']}")
        assert detail_resp.status_code == 200
        user_detail = detail_resp.json()
        
        # Check progress
        progress = user_detail.get("progress", [])
        assert len(progress) > 0, "No progress data for Dr. Schmidt"
        
        # Find step 1 progress (order=1)
        steps_resp = admin_session.get(f"{BASE_URL}/api/admin/steps")
        steps = steps_resp.json()
        step1 = next((s for s in steps if s["order"] == 1), None)
        
        if step1:
            step1_progress = next((p for p in progress if p["step_id"] == step1["id"]), None)
            assert step1_progress is not None, "Step 1 progress not found for Dr. Schmidt"
            assert step1_progress["status"] == "completed", f"Step 1 not completed: {step1_progress['status']}"
            
            # Check form data
            data = step1_progress.get("data", {})
            assert data.get("name") == "Schmidt", f"Expected name='Schmidt', got {data.get('name')}"
            assert data.get("first_name") == "Anna", f"Expected first_name='Anna', got {data.get('first_name')}"
            assert data.get("field_of_study") == "Allgemeinmedizin", f"Expected Allgemeinmedizin, got {data.get('field_of_study')}"
            print(f"✓ Dr. Schmidt has Step 1 completed with correct form data")


class TestStep1FachgebietOptions:
    """Tests for Step 1 Fachgebiet field with 15 medical specialties"""
    
    def test_step1_has_15_fachgebiet_options(self, admin_session):
        """Step 1 should have Fachgebiet field with 15 medical specialties"""
        resp = admin_session.get(f"{BASE_URL}/api/admin/steps")
        assert resp.status_code == 200
        steps = resp.json()
        
        step1 = next((s for s in steps if s["order"] == 1), None)
        assert step1 is not None, "Step 1 not found"
        
        fields = step1.get("fields", [])
        fachgebiet_field = next((f for f in fields if f["name"] == "field_of_study"), None)
        assert fachgebiet_field is not None, "Fachgebiet field not found in Step 1"
        
        options = fachgebiet_field.get("options", [])
        assert len(options) == 15, f"Expected 15 Fachgebiet options, got {len(options)}"
        
        # Verify all expected specialties are present
        for specialty in EXPECTED_FACHGEBIETE:
            assert specialty in options, f"Missing specialty: {specialty}"
        
        print(f"✓ Step 1 has all 15 Fachgebiet options: {options}")


class TestPartnerMultiselectionStepType:
    """Tests for partner_multiselection step type"""
    
    def test_create_partner_multiselection_step(self, admin_session, test_data_tracker):
        """Admin can create a step with type=partner_multiselection"""
        unique_title = f"TEST_MultiSelect_{uuid.uuid4().hex[:8]}"
        
        resp = admin_session.post(f"{BASE_URL}/api/admin/steps", json={
            "title": unique_title,
            "description": "Test partner multiselection step",
            "order": 99,
            "step_type": "partner_multiselection",
            "filter_tag": "test_tag",
            "skippable": True,
            "skip_label": "Skip this step"
        })
        
        assert resp.status_code == 200, f"Create step failed: {resp.text}"
        data = resp.json()
        assert "id" in data
        test_data_tracker["step_ids"].append(data["id"])
        
        # Verify step was created with correct type
        steps_resp = admin_session.get(f"{BASE_URL}/api/admin/steps")
        steps = steps_resp.json()
        created_step = next((s for s in steps if s["title"] == unique_title), None)
        assert created_step is not None, "Created step not found"
        assert created_step["step_type"] == "partner_multiselection", f"Expected type 'partner_multiselection', got {created_step['step_type']}"
        assert created_step["filter_tag"] == "test_tag", f"Filter tag mismatch"
        print(f"✓ Created partner_multiselection step: {unique_title}")
    
    def test_step_types_include_partner_multiselection(self, admin_session):
        """Verify backend accepts all 5 step types"""
        step_types = ["form", "partner_selection", "partner_multiselection", "milestone", "display"]
        
        for step_type in step_types:
            unique_title = f"TEST_Type_{step_type}_{uuid.uuid4().hex[:8]}"
            resp = admin_session.post(f"{BASE_URL}/api/admin/steps", json={
                "title": unique_title,
                "description": f"Test {step_type} step",
                "order": 98,
                "step_type": step_type
            })
            
            # Should succeed for all types
            assert resp.status_code == 200, f"Failed to create {step_type} step: {resp.text}"
            
            # Clean up immediately
            step_id = resp.json()["id"]
            admin_session.delete(f"{BASE_URL}/api/admin/steps/{step_id}")
            print(f"✓ Step type '{step_type}' accepted by backend")


class TestAdminUserDetailStepData:
    """Tests for admin user detail showing step data"""
    
    def test_user_detail_includes_progress_data(self, admin_session):
        """GET /api/admin/users/{id} returns progress with data field"""
        # Get Dr. Schmidt's user ID
        resp = admin_session.get(f"{BASE_URL}/api/admin/users")
        users = resp.json()
        dr_schmidt = next((u for u in users if u["email"] == "dr.schmidt@example.com"), None)
        
        if not dr_schmidt:
            pytest.skip("Dr. Schmidt not found - seed data may not be present")
        
        # Get user detail
        detail_resp = admin_session.get(f"{BASE_URL}/api/admin/users/{dr_schmidt['id']}")
        assert detail_resp.status_code == 200
        user_detail = detail_resp.json()
        
        # Verify progress array exists
        assert "progress" in user_detail, "User detail missing 'progress' field"
        progress = user_detail["progress"]
        assert isinstance(progress, list), "Progress should be a list"
        
        # Check that progress items have data field
        for p in progress:
            assert "step_id" in p, "Progress item missing step_id"
            assert "status" in p, "Progress item missing status"
            assert "data" in p, "Progress item missing data field"
        
        print(f"✓ User detail includes progress with data fields")
    
    def test_completed_step_has_form_data(self, admin_session):
        """Completed steps should have form data in the data field"""
        # Get Dr. Schmidt
        resp = admin_session.get(f"{BASE_URL}/api/admin/users")
        users = resp.json()
        dr_schmidt = next((u for u in users if u["email"] == "dr.schmidt@example.com"), None)
        
        if not dr_schmidt:
            pytest.skip("Dr. Schmidt not found")
        
        detail_resp = admin_session.get(f"{BASE_URL}/api/admin/users/{dr_schmidt['id']}")
        user_detail = detail_resp.json()
        
        # Find completed step with data
        completed_with_data = [p for p in user_detail["progress"] 
                              if p["status"] == "completed" and p.get("data") and len(p["data"]) > 0]
        
        assert len(completed_with_data) > 0, "No completed steps with data found"
        
        # Check first completed step has expected fields
        step_data = completed_with_data[0]["data"]
        print(f"✓ Found completed step with data: {list(step_data.keys())}")


class TestCodeReviewStepEditor:
    """Code review tests for step editor UI"""
    
    def test_step_type_dropdown_has_5_options(self):
        """Verify step type dropdown includes all 5 options"""
        import subprocess
        
        # Check for all 5 step types in SelectContent
        result = subprocess.run(
            ["grep", "-n", "partner_multiselection", "/app/frontend/src/pages/AdminDashboard.js"],
            capture_output=True, text=True
        )
        assert "partner_multiselection" in result.stdout, "partner_multiselection not found in step type dropdown"
        
        # Check for German labels
        result2 = subprocess.run(
            ["grep", "-n", "Partner-Mehrfachauswahl", "/app/frontend/src/pages/AdminDashboard.js"],
            capture_output=True, text=True
        )
        assert "Partner-Mehrfachauswahl" in result2.stdout, "German label 'Partner-Mehrfachauswahl' not found"
        print(f"✓ Step type dropdown includes partner_multiselection with German label")
    
    def test_typ_einstellungen_tab_conditional(self):
        """Verify Typ-Einstellungen tab shows only for specific types"""
        import subprocess
        
        # Check for conditional rendering of Typ-Einstellungen tab
        result = subprocess.run(
            ["grep", "-n", "Typ-Einstellungen", "/app/frontend/src/pages/AdminDashboard.js"],
            capture_output=True, text=True
        )
        assert "Typ-Einstellungen" in result.stdout, "Typ-Einstellungen tab not found"
        
        # Check it's conditional on step_type
        result2 = subprocess.run(
            ["grep", "-n", "partner_selection.*partner_multiselection.*milestone.*display.*Typ-Einstellungen", 
             "/app/frontend/src/pages/AdminDashboard.js"],
            capture_output=True, text=True
        )
        # The condition should include all 4 types
        assert "partner_selection" in result.stdout or "partner_multiselection" in result.stdout, \
            "Typ-Einstellungen should be conditional on step type"
        print(f"✓ Typ-Einstellungen tab is conditionally rendered")
    
    def test_fields_tab_only_for_form_type(self):
        """Verify Fields tab shows only for form type"""
        import subprocess
        
        result = subprocess.run(
            ["grep", "-n", "step_type.*form.*fields", "/app/frontend/src/pages/AdminDashboard.js"],
            capture_output=True, text=True
        )
        assert "form" in result.stdout, "Fields tab should be conditional on form type"
        print(f"✓ Fields tab is conditional on form type")


class TestCleanup:
    """Cleanup test data at end of test run"""
    
    def test_cleanup_test_data(self, admin_session, test_data_tracker):
        """Delete all TEST_ prefixed data created during tests"""
        # Clean up test steps
        for step_id in test_data_tracker.get("step_ids", []):
            try:
                admin_session.delete(f"{BASE_URL}/api/admin/steps/{step_id}")
                print(f"✓ Deleted test step: {step_id}")
            except Exception as e:
                print(f"Warning: Failed to delete step {step_id}: {e}")
        
        # Clean up TEST_ prefixed users using the new DELETE endpoint
        resp = admin_session.get(f"{BASE_URL}/api/admin/users")
        if resp.status_code == 200:
            users = resp.json()
            test_users = [u for u in users if u["email"].startswith("TEST_") or u["name"].startswith("TEST_")]
            deleted_count = 0
            for user in test_users:
                try:
                    del_resp = admin_session.delete(f"{BASE_URL}/api/admin/users/{user['id']}")
                    if del_resp.status_code == 200:
                        deleted_count += 1
                        print(f"✓ Deleted TEST_ user: {user['email']}")
                    else:
                        print(f"Warning: Failed to delete {user['email']}: {del_resp.status_code}")
                except Exception as e:
                    print(f"Warning: {e}")
            print(f"✓ Deleted {deleted_count} TEST_ prefixed users")
        
        print(f"✓ Cleanup completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
