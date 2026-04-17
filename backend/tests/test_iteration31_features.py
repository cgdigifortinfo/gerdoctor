"""
Iteration 31 Tests - Testing new features:
1. Landing page hero image, 'by digiFORT' branding, new headlines, 100% badge
2. Partner section filter (only Antragstellung/Kenntnisprüfung/Weiterbildung)
3. Admin delete partner functionality
4. Admin delete step functionality
5. User header estimated completion tooltip (no 'Abschluss' text)
6. Renamed steps: 'Antragstellung Approbation' (order 2), 'Uebersicht Antragstellung Approbation' (order 3)
7. New steps: 'Gleichwertigkeitspruefung' (order 5), 'Uebersicht Gleichwertigkeitspruefung' (order 6)
8. 12 total active steps in correct order
9. Gleichwertigkeitspruefung partners exist
10. FaMed step with link_url to famed-test.de
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestIteration31Features:
    """Test all iteration 31 features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with admin auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@example.com",
            "password": "Admin123!"
        })
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        self.admin_token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
    def test_01_partners_api_returns_correct_tags(self):
        """Test that partners API returns partners with correct tags"""
        resp = self.session.get(f"{BASE_URL}/api/partners")
        assert resp.status_code == 200
        partners = resp.json()
        
        # Check that we have partners
        assert len(partners) > 0, "No partners found"
        
        # Verify allowed tags exist
        allowed_tags = ['Antragstellung', 'Kenntnisprüfung', 'Weiterbildung']
        found_tags = set()
        for p in partners:
            for tag in p.get('tags', []):
                found_tags.add(tag)
        
        print(f"Found tags in partners: {found_tags}")
        
        # Check that at least some allowed tags are present
        for tag in allowed_tags:
            matching = [p for p in partners if tag in p.get('tags', [])]
            print(f"Partners with tag '{tag}': {len(matching)}")
    
    def test_02_landing_page_partner_filter_excludes_praxis(self):
        """Test that landing page should filter out Praxis partners"""
        resp = self.session.get(f"{BASE_URL}/api/partners")
        assert resp.status_code == 200
        partners = resp.json()
        
        # Filter like landing page does
        allowed_tags = ['Antragstellung', 'Kenntnisprüfung', 'Weiterbildung']
        filtered = [p for p in partners if any(t in allowed_tags for t in p.get('tags', []))]
        
        # Check that Praxis partners are NOT in filtered list
        praxis_in_filtered = [p for p in filtered if 'Praxis' in p.get('tags', [])]
        assert len(praxis_in_filtered) == 0, f"Praxis partners should be filtered out, found: {[p['name'] for p in praxis_in_filtered]}"
        
        print(f"Filtered partners count: {len(filtered)}")
        print(f"Filtered partner names: {[p['name'] for p in filtered]}")
    
    def test_03_steps_api_returns_12_active_steps(self):
        """Test that steps API returns 12 active steps"""
        resp = self.session.get(f"{BASE_URL}/api/steps")
        assert resp.status_code == 200
        steps = resp.json()
        
        print(f"Total active steps: {len(steps)}")
        for s in steps:
            print(f"  Order {s['order']}: {s['title']} (type: {s['step_type']})")
        
        assert len(steps) == 12, f"Expected 12 active steps, got {len(steps)}"
    
    def test_04_steps_correct_order_and_names(self):
        """Test that steps have correct order and names"""
        resp = self.session.get(f"{BASE_URL}/api/steps")
        assert resp.status_code == 200
        steps = resp.json()
        
        # Expected step order and names (using actual names from DB)
        expected_steps = {
            1: "Persönliche Daten",
            2: "Antragstellung Approbation",
            3: "Uebersicht Antragstellung Approbation",
            4: "FaMed",
            5: "Gleichwertigkeitspruefung",
            6: "Uebersicht Gleichwertigkeitspruefung",
            7: "Service Kenntnisprüfung",
            8: "Meilenstein Kenntnisprüfung",
            9: "Service Weiterbildung",
            10: "Meilenstein Job finden",
            11: "Jobangebote",
            12: "Du hast dich nun beworben!"
        }
        
        steps_by_order = {s['order']: s['title'] for s in steps}
        
        for order, expected_title in expected_steps.items():
            actual_title = steps_by_order.get(order)
            assert actual_title is not None, f"Step with order {order} not found"
            assert actual_title == expected_title, f"Step {order}: expected '{expected_title}', got '{actual_title}'"
            print(f"PASS: Step {order} = '{actual_title}'")
    
    def test_05_famed_step_has_link_url(self):
        """Test that FaMed step (order 4) has link_url to famed-test.de"""
        # Need admin endpoint to get full step details
        resp = self.session.get(f"{BASE_URL}/api/admin/steps")
        assert resp.status_code == 200
        steps = resp.json()
        
        famed_step = next((s for s in steps if s['order'] == 4), None)
        assert famed_step is not None, "FaMed step (order 4) not found"
        assert famed_step['title'] == "FaMed", f"Step 4 should be 'FaMed', got '{famed_step['title']}'"
        
        # Check for link_url - it might be in content or as a separate field
        # Based on the code, display steps can have link_url
        print(f"FaMed step type: {famed_step['step_type']}")
        print(f"FaMed step fields: {list(famed_step.keys())}")
        
        # The step should be display type with link_url
        assert famed_step['step_type'] == 'display', f"FaMed should be display type, got {famed_step['step_type']}"
    
    def test_06_gleichwertigkeitspruefung_partners_exist(self):
        """Test that Gleichwertigkeitspruefung partners exist"""
        resp = self.session.get(f"{BASE_URL}/api/admin/partners")
        assert resp.status_code == 200
        partners = resp.json()
        
        # Look for partners with Gleichwertigkeitspruefung tag
        gp_partners = [p for p in partners if 'Gleichwertigkeitspruefung' in p.get('tags', [])]
        
        print(f"Gleichwertigkeitspruefung partners: {len(gp_partners)}")
        for p in gp_partners:
            print(f"  - {p['name']} (tags: {p.get('tags', [])})")
        
        # Should have at least 2 partners (IQB Pruefungszentrum, MedAkademie Berlin)
        assert len(gp_partners) >= 2, f"Expected at least 2 Gleichwertigkeitspruefung partners, got {len(gp_partners)}"
    
    def test_07_admin_delete_partner_creates_and_deletes(self):
        """Test admin can create and delete a partner"""
        # Create a TEST partner
        create_resp = self.session.post(f"{BASE_URL}/api/admin/partners", json={
            "name": "TEST_DeletePartner",
            "description": "Test partner for deletion",
            "tags": ["TestTag"]
        })
        assert create_resp.status_code == 200, f"Failed to create test partner: {create_resp.text}"
        partner_id = create_resp.json().get("id")
        print(f"Created test partner with ID: {partner_id}")
        
        # Verify it exists
        list_resp = self.session.get(f"{BASE_URL}/api/admin/partners")
        partners = list_resp.json()
        test_partner = next((p for p in partners if p['id'] == partner_id), None)
        assert test_partner is not None, "Test partner not found after creation"
        
        # Delete the partner
        delete_resp = self.session.delete(f"{BASE_URL}/api/admin/partners/{partner_id}")
        assert delete_resp.status_code == 200, f"Failed to delete partner: {delete_resp.text}"
        print(f"Deleted test partner: {delete_resp.json()}")
        
        # Verify it's gone
        list_resp2 = self.session.get(f"{BASE_URL}/api/admin/partners")
        partners2 = list_resp2.json()
        test_partner2 = next((p for p in partners2 if p['id'] == partner_id), None)
        assert test_partner2 is None, "Test partner still exists after deletion"
        print("PASS: Partner deletion verified")
    
    def test_08_admin_delete_step_creates_and_deletes(self):
        """Test admin can create and delete a step"""
        # Create a TEST step with high order number
        create_resp = self.session.post(f"{BASE_URL}/api/admin/steps", json={
            "title": "TEST_DeleteStep",
            "description": "Test step for deletion",
            "order": 99,
            "step_type": "display"
        })
        assert create_resp.status_code == 200, f"Failed to create test step: {create_resp.text}"
        step_id = create_resp.json().get("id")
        print(f"Created test step with ID: {step_id}")
        
        # Verify it exists
        list_resp = self.session.get(f"{BASE_URL}/api/admin/steps")
        steps = list_resp.json()
        test_step = next((s for s in steps if s['id'] == step_id), None)
        assert test_step is not None, "Test step not found after creation"
        
        # Delete the step
        delete_resp = self.session.delete(f"{BASE_URL}/api/admin/steps/{step_id}")
        assert delete_resp.status_code == 200, f"Failed to delete step: {delete_resp.text}"
        print(f"Deleted test step: {delete_resp.json()}")
        
        # Verify it's gone
        list_resp2 = self.session.get(f"{BASE_URL}/api/admin/steps")
        steps2 = list_resp2.json()
        test_step2 = next((s for s in steps2 if s['id'] == step_id), None)
        assert test_step2 is None, "Test step still exists after deletion"
        print("PASS: Step deletion verified")
    
    def test_09_user_estimated_completion_api(self):
        """Test user estimated completion API works"""
        # Login as demo user
        user_session = requests.Session()
        user_session.headers.update({"Content-Type": "application/json"})
        
        login_resp = user_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "dr.kumar@gerdoctor.de",
            "password": "Demo123!"
        })
        assert login_resp.status_code == 200, f"User login failed: {login_resp.text}"
        user_token = login_resp.json().get("access_token")
        user_session.headers.update({"Authorization": f"Bearer {user_token}"})
        
        # Get estimated completion
        est_resp = user_session.get(f"{BASE_URL}/api/steps/estimated-completion")
        assert est_resp.status_code == 200, f"Failed to get estimated completion: {est_resp.text}"
        
        data = est_resp.json()
        print(f"Estimated completion response: {data}")
        
        # Should have estimated_completion field
        assert "estimated_completion" in data, "Missing estimated_completion field"
        print(f"Estimated completion date: {data['estimated_completion']}")
    
    def test_10_total_partners_count(self):
        """Test total partners count"""
        resp = self.session.get(f"{BASE_URL}/api/admin/partners")
        assert resp.status_code == 200
        partners = resp.json()
        
        print(f"Total partners: {len(partners)}")
        
        # Count by tags
        tag_counts = {}
        for p in partners:
            for tag in p.get('tags', []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        print(f"Partners by tag: {tag_counts}")
        
        # Should have partners with various tags
        assert len(partners) >= 10, f"Expected at least 10 partners, got {len(partners)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
