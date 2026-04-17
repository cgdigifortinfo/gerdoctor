"""
Iteration 30 Tests: Partner Selection Pre-fill, Logo URLs, and Filter Dropdown
Tests for:
1. Multi-partner selection pre-fill when navigating back to step 9 (Jobangebote)
2. Partner logos are loading (not broken 404s)
3. Filter dropdown on partner_selection and partner_multiselection views
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPartnerLogos:
    """Test that partner logos are valid URLs and not returning 404"""
    
    def test_all_partner_logos_are_valid(self):
        """All 17 partners should have valid logo URLs that don't return 404"""
        response = requests.get(f"{BASE_URL}/api/partners")
        assert response.status_code == 200, f"Failed to get partners: {response.status_code}"
        
        partners = response.json()
        assert len(partners) == 17, f"Expected 17 partners, got {len(partners)}"
        
        broken_logos = []
        for partner in partners:
            logo_url = partner.get('logo_url', '')
            if logo_url:
                # Check if logo URL is accessible
                try:
                    logo_response = requests.head(logo_url, timeout=10)
                    if logo_response.status_code >= 400:
                        broken_logos.append({
                            'partner': partner['name'],
                            'logo_url': logo_url,
                            'status': logo_response.status_code
                        })
                except Exception as e:
                    broken_logos.append({
                        'partner': partner['name'],
                        'logo_url': logo_url,
                        'error': str(e)
                    })
        
        assert len(broken_logos) == 0, f"Found broken logos: {broken_logos}"
        print(f"PASS: All {len(partners)} partner logos are valid")
    
    def test_partner_logos_use_emergent_static_images(self):
        """Partner logos should use Emergent static image URLs, not external digifort-experts.de"""
        response = requests.get(f"{BASE_URL}/api/partners")
        assert response.status_code == 200
        
        partners = response.json()
        external_logos = []
        
        for partner in partners:
            logo_url = partner.get('logo_url', '')
            if 'digifort-experts.de' in logo_url:
                external_logos.append({
                    'partner': partner['name'],
                    'logo_url': logo_url
                })
        
        assert len(external_logos) == 0, f"Found external digifort-experts.de logos: {external_logos}"
        print("PASS: No external digifort-experts.de logos found")


class TestPartnerFiltering:
    """Test partner filtering by tag/category"""
    
    def test_partners_filter_by_praxis_tag(self):
        """GET /api/partners?tag=Praxis should return only Praxis partners"""
        response = requests.get(f"{BASE_URL}/api/partners?tag=Praxis")
        assert response.status_code == 200
        
        partners = response.json()
        assert len(partners) == 9, f"Expected 9 Praxis partners, got {len(partners)}"
        
        for partner in partners:
            assert 'Praxis' in partner.get('tags', []), f"Partner {partner['name']} doesn't have Praxis tag"
        
        print(f"PASS: Filter by Praxis tag returns {len(partners)} partners")
    
    def test_partners_filter_by_antragstellung_tag(self):
        """GET /api/partners?tag=Antragstellung should return Antragstellung partners"""
        response = requests.get(f"{BASE_URL}/api/partners?tag=Antragstellung")
        assert response.status_code == 200
        
        partners = response.json()
        assert len(partners) >= 2, f"Expected at least 2 Antragstellung partners, got {len(partners)}"
        
        for partner in partners:
            assert 'Antragstellung' in partner.get('tags', []), f"Partner {partner['name']} doesn't have Antragstellung tag"
        
        print(f"PASS: Filter by Antragstellung tag returns {len(partners)} partners")
    
    def test_praxis_partners_have_unique_categories(self):
        """Praxis partners should have unique categories for filter dropdown"""
        response = requests.get(f"{BASE_URL}/api/partners?tag=Praxis")
        assert response.status_code == 200
        
        partners = response.json()
        categories = set()
        
        for partner in partners:
            category = partner.get('category', '')
            if category:
                categories.add(category)
        
        # Expected categories: HNO, Allgemeinmedizin, Innere Medizin, Chirurgie, Paediatrie, 
        # Dermatologie, Neurologie, Orthopaedie, Gynaekologie
        expected_categories = {
            'HNO', 'Allgemeinmedizin', 'Innere Medizin', 'Chirurgie', 
            'Paediatrie', 'Dermatologie', 'Neurologie', 'Orthopaedie', 'Gynaekologie'
        }
        
        assert categories == expected_categories, f"Expected categories {expected_categories}, got {categories}"
        print(f"PASS: Praxis partners have {len(categories)} unique categories: {categories}")


class TestPartnerSelectionPrefill:
    """Test partner selection pre-fill when navigating back to completed steps"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@example.com",
            "password": "Admin123!"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()['access_token']
    
    @pytest.fixture
    def cg_user_token(self, admin_token):
        """Get cg@digifort.info user token via impersonation"""
        # Get user ID
        users_response = requests.get(f"{BASE_URL}/api/admin/users", 
            headers={"Authorization": f"Bearer {admin_token}"})
        assert users_response.status_code == 200
        
        cg_user = None
        for user in users_response.json():
            if user['email'] == 'cg@digifort.info':
                cg_user = user
                break
        
        assert cg_user is not None, "cg@digifort.info user not found"
        
        # Impersonate
        impersonate_response = requests.post(
            f"{BASE_URL}/api/admin/impersonate/{cg_user['id']}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert impersonate_response.status_code == 200, f"Impersonation failed: {impersonate_response.text}"
        return impersonate_response.json()['access_token']
    
    def test_cg_user_step9_has_4_partners_selected(self, cg_user_token):
        """cg@digifort.info user should have Step 9 completed with 4 partners"""
        response = requests.get(f"{BASE_URL}/api/steps/progress",
            headers={"Authorization": f"Bearer {cg_user_token}"})
        assert response.status_code == 200
        
        progress = response.json()
        
        # Find the step with selected_partner_ids
        multiselection_step = None
        for p in progress:
            if 'selected_partner_ids' in p.get('data', {}):
                multiselection_step = p
                break
        
        assert multiselection_step is not None, "No partner_multiselection step found with selected_partner_ids"
        assert multiselection_step['status'] == 'completed', "Step 9 should be completed"
        
        selected_ids = multiselection_step['data']['selected_partner_ids']
        assert len(selected_ids) == 4, f"Expected 4 selected partners, got {len(selected_ids)}"
        
        print(f"PASS: cg user has Step 9 completed with 4 partners: {selected_ids}")
    
    def test_dr_kumar_step2_has_partner_selected(self):
        """dr.kumar@gerdoctor.de should have Step 2 completed with HABS e.V. partner"""
        # Login as dr.kumar
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "dr.kumar@gerdoctor.de",
            "password": "Demo123!"
        })
        assert response.status_code == 200, f"Dr. Kumar login failed: {response.text}"
        token = response.json()['access_token']
        
        # Get progress
        progress_response = requests.get(f"{BASE_URL}/api/steps/progress",
            headers={"Authorization": f"Bearer {token}"})
        assert progress_response.status_code == 200
        
        progress = progress_response.json()
        
        # Find step with selected_partner_id (partner_selection step)
        partner_selection_step = None
        for p in progress:
            if 'selected_partner_id' in p.get('data', {}):
                partner_selection_step = p
                break
        
        assert partner_selection_step is not None, "No partner_selection step found"
        assert partner_selection_step['status'] == 'completed', "Step should be completed"
        assert 'HABS' in partner_selection_step['data'].get('selected_partner_name', ''), \
            f"Expected HABS e.V., got {partner_selection_step['data'].get('selected_partner_name')}"
        
        print(f"PASS: Dr. Kumar has partner_selection step completed with {partner_selection_step['data']['selected_partner_name']}")


class TestStepsAPI:
    """Test steps API returns correct step types and filter tags"""
    
    def test_steps_have_correct_types_and_filter_tags(self):
        """Steps should have correct step_type and filter_tag for partner selection"""
        # Login as any user
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "dr.kumar@gerdoctor.de",
            "password": "Demo123!"
        })
        assert response.status_code == 200
        token = response.json()['access_token']
        
        # Get steps
        steps_response = requests.get(f"{BASE_URL}/api/steps",
            headers={"Authorization": f"Bearer {token}"})
        assert steps_response.status_code == 200
        
        steps = steps_response.json()
        
        # Find partner_selection and partner_multiselection steps
        partner_selection_steps = [s for s in steps if s['step_type'] == 'partner_selection']
        partner_multiselection_steps = [s for s in steps if s['step_type'] == 'partner_multiselection']
        
        assert len(partner_selection_steps) >= 3, f"Expected at least 3 partner_selection steps, got {len(partner_selection_steps)}"
        assert len(partner_multiselection_steps) >= 1, f"Expected at least 1 partner_multiselection step, got {len(partner_multiselection_steps)}"
        
        # Check Jobangebote step (partner_multiselection with Praxis filter)
        jobangebote_step = None
        for s in partner_multiselection_steps:
            if s.get('filter_tag') == 'Praxis':
                jobangebote_step = s
                break
        
        assert jobangebote_step is not None, "Jobangebote step (partner_multiselection with Praxis filter) not found"
        assert jobangebote_step['title'] == 'Jobangebote', f"Expected title 'Jobangebote', got {jobangebote_step['title']}"
        
        print(f"PASS: Found {len(partner_selection_steps)} partner_selection steps and {len(partner_multiselection_steps)} partner_multiselection steps")
        print(f"PASS: Jobangebote step has filter_tag='Praxis'")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
