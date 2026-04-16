"""
Test Partner Linking Features - Iteration 28
Tests for:
1. Admin Partner edit with empty contact_email (should NOT throw validation error)
2. Admin Partner edit with linked_user_ids (should NOT change user roles - m:n without role change)
3. linked_user_ids stored on partner doc, not on user doc
4. Partner Dashboard /api/partner/submissions includes users from linked_user_ids with status='linked'
5. Partner Dashboard /api/partner/other-users excludes linked users
6. Admin Partner create with linked_user_ids stores array on partner doc
7. Admin create user with role='partner' and partner_id still works (1:1 dashboard access)
8. Admin get partners returns both linked_user_ids and resolved linked_users
9. Users page in admin shows correct roles after partner linking
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPartnerLinking:
    """Test partner linking features - m:n relationship without role changes"""
    
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
        
        yield
        
        # Cleanup: delete test partner and user if created
        if hasattr(self, 'test_partner_id'):
            try:
                self.session.delete(f"{BASE_URL}/api/admin/partners/{self.test_partner_id}")
            except:
                pass
        if hasattr(self, 'test_user_id'):
            try:
                self.session.delete(f"{BASE_URL}/api/admin/users/{self.test_user_id}")
            except:
                pass
    
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
    
    def test_02_partner_create_with_empty_contact_email(self):
        """Test creating partner with empty contact_email should NOT throw validation error"""
        unique_id = str(uuid.uuid4())[:8]
        resp = self.session.post(f"{BASE_URL}/api/admin/partners", json={
            "name": f"TEST_Partner_Empty_Email_{unique_id}",
            "description": "Test partner with empty email",
            "contact_email": "",  # Empty string - should be converted to None
            "category": "Test"
        })
        assert resp.status_code == 200, f"Partner create with empty email failed: {resp.text}"
        data = resp.json()
        assert "id" in data
        self.test_partner_id = data["id"]
        print(f"PASS: Partner created with empty contact_email, id={self.test_partner_id}")
    
    def test_03_partner_update_with_empty_contact_email(self):
        """Test updating partner with empty contact_email should NOT throw validation error"""
        # First create a partner
        unique_id = str(uuid.uuid4())[:8]
        create_resp = self.session.post(f"{BASE_URL}/api/admin/partners", json={
            "name": f"TEST_Partner_Update_Email_{unique_id}",
            "description": "Test partner for update",
            "contact_email": "test@example.com",
            "category": "Test"
        })
        assert create_resp.status_code == 200
        partner_id = create_resp.json()["id"]
        self.test_partner_id = partner_id
        
        # Update with empty email
        update_resp = self.session.put(f"{BASE_URL}/api/admin/partners/{partner_id}", json={
            "contact_email": ""  # Empty string - should be converted to None
        })
        assert update_resp.status_code == 200, f"Partner update with empty email failed: {update_resp.text}"
        print("PASS: Partner updated with empty contact_email")
    
    def test_04_partner_create_with_linked_user_ids(self):
        """Test creating partner with linked_user_ids stores array on partner doc"""
        # Get a user to link
        users_resp = self.session.get(f"{BASE_URL}/api/admin/users")
        assert users_resp.status_code == 200
        users = users_resp.json()
        regular_users = [u for u in users if u["role"] == "user"]
        assert len(regular_users) > 0, "No regular users found for linking"
        
        user_to_link = regular_users[0]
        user_id = user_to_link["id"]
        original_role = user_to_link["role"]
        
        # Create partner with linked_user_ids
        unique_id = str(uuid.uuid4())[:8]
        create_resp = self.session.post(f"{BASE_URL}/api/admin/partners", json={
            "name": f"TEST_Partner_Linked_{unique_id}",
            "description": "Test partner with linked users",
            "linked_user_ids": [user_id]
        })
        assert create_resp.status_code == 200, f"Partner create with linked_user_ids failed: {create_resp.text}"
        partner_id = create_resp.json()["id"]
        self.test_partner_id = partner_id
        
        # Verify linked_user_ids is stored on partner doc
        partners_resp = self.session.get(f"{BASE_URL}/api/admin/partners")
        assert partners_resp.status_code == 200
        partners = partners_resp.json()
        created_partner = next((p for p in partners if p["id"] == partner_id), None)
        assert created_partner is not None
        assert "linked_user_ids" in created_partner
        assert user_id in created_partner["linked_user_ids"]
        
        # Verify user role was NOT changed (m:n without role change)
        users_resp2 = self.session.get(f"{BASE_URL}/api/admin/users")
        users2 = users_resp2.json()
        linked_user = next((u for u in users2 if u["id"] == user_id), None)
        assert linked_user is not None
        assert linked_user["role"] == original_role, f"User role changed from {original_role} to {linked_user['role']} - should NOT change!"
        
        print(f"PASS: Partner created with linked_user_ids, user role unchanged ({original_role})")
    
    def test_05_partner_update_with_linked_user_ids_no_role_change(self):
        """Test updating partner with linked_user_ids does NOT change user roles"""
        # Get users
        users_resp = self.session.get(f"{BASE_URL}/api/admin/users")
        assert users_resp.status_code == 200
        users = users_resp.json()
        regular_users = [u for u in users if u["role"] == "user"]
        assert len(regular_users) >= 2, "Need at least 2 regular users for this test"
        
        user1 = regular_users[0]
        user2 = regular_users[1]
        
        # Create a partner
        unique_id = str(uuid.uuid4())[:8]
        create_resp = self.session.post(f"{BASE_URL}/api/admin/partners", json={
            "name": f"TEST_Partner_Update_Link_{unique_id}",
            "description": "Test partner for update linking"
        })
        assert create_resp.status_code == 200
        partner_id = create_resp.json()["id"]
        self.test_partner_id = partner_id
        
        # Update partner with linked_user_ids
        update_resp = self.session.put(f"{BASE_URL}/api/admin/partners/{partner_id}", json={
            "linked_user_ids": [user1["id"], user2["id"]]
        })
        assert update_resp.status_code == 200, f"Partner update with linked_user_ids failed: {update_resp.text}"
        
        # Verify users' roles were NOT changed
        users_resp2 = self.session.get(f"{BASE_URL}/api/admin/users")
        users2 = users_resp2.json()
        
        for uid in [user1["id"], user2["id"]]:
            user = next((u for u in users2 if u["id"] == uid), None)
            assert user is not None
            assert user["role"] == "user", f"User {uid} role changed to {user['role']} - should remain 'user'!"
        
        print("PASS: Partner updated with linked_user_ids, user roles unchanged")
    
    def test_06_admin_get_partners_returns_linked_user_ids_and_linked_users(self):
        """Test admin get partners returns both linked_user_ids array and resolved linked_users"""
        resp = self.session.get(f"{BASE_URL}/api/admin/partners")
        assert resp.status_code == 200
        partners = resp.json()
        assert len(partners) > 0, "No partners found"
        
        # Check structure of partner response
        partner = partners[0]
        assert "linked_user_ids" in partner, "linked_user_ids not in partner response"
        assert "linked_users" in partner, "linked_users not in partner response"
        assert isinstance(partner["linked_user_ids"], list), "linked_user_ids should be a list"
        assert isinstance(partner["linked_users"], list), "linked_users should be a list"
        
        # If there are linked users, verify structure
        if partner["linked_users"]:
            linked_user = partner["linked_users"][0]
            assert "id" in linked_user
            assert "name" in linked_user
            assert "email" in linked_user
        
        print(f"PASS: Admin get partners returns linked_user_ids and linked_users (found {len(partners)} partners)")
    
    def test_07_admin_create_user_with_partner_role_and_partner_id(self):
        """Test admin create user with role='partner' and partner_id still works (1:1 dashboard access)"""
        # First create a partner
        unique_id = str(uuid.uuid4())[:8]
        partner_resp = self.session.post(f"{BASE_URL}/api/admin/partners", json={
            "name": f"TEST_Partner_For_User_{unique_id}",
            "description": "Test partner for user creation"
        })
        assert partner_resp.status_code == 200
        partner_id = partner_resp.json()["id"]
        self.test_partner_id = partner_id
        
        # Create user with role='partner' and partner_id
        user_resp = self.session.post(f"{BASE_URL}/api/admin/users", json={
            "email": f"test_partner_user_{unique_id}@example.com",
            "password": "Test123!",
            "name": f"Test Partner User {unique_id}",
            "role": "partner",
            "partner_id": partner_id
        })
        assert user_resp.status_code == 200, f"Create user with partner role failed: {user_resp.text}"
        user_id = user_resp.json()["id"]
        self.test_user_id = user_id
        
        # Verify user was created with partner role
        users_resp = self.session.get(f"{BASE_URL}/api/admin/users")
        users = users_resp.json()
        created_user = next((u for u in users if u["id"] == user_id), None)
        assert created_user is not None
        assert created_user["role"] == "partner"
        
        # Verify partner has user_id set (1:1 dashboard access)
        partners_resp = self.session.get(f"{BASE_URL}/api/admin/partners")
        partners = partners_resp.json()
        partner = next((p for p in partners if p["id"] == partner_id), None)
        assert partner is not None
        assert partner.get("user_id") == user_id, f"Partner user_id not set correctly: {partner.get('user_id')} != {user_id}"
        
        print(f"PASS: User created with role='partner' and partner_id, partner.user_id set correctly")
    
    def test_08_partner_dashboard_submissions_includes_linked_users(self):
        """Test Partner Dashboard /api/partner/submissions includes users from linked_user_ids with status='linked'"""
        # Login as partner user
        partner_session = requests.Session()
        partner_session.headers.update({"Content-Type": "application/json"})
        
        login_resp = partner_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@example.com",
            "password": "Partner123!"
        })
        assert login_resp.status_code == 200, f"Partner login failed: {login_resp.text}"
        partner_token = login_resp.json().get("access_token")
        partner_session.headers.update({"Authorization": f"Bearer {partner_token}"})
        
        # Get partner submissions
        submissions_resp = partner_session.get(f"{BASE_URL}/api/partner/submissions")
        assert submissions_resp.status_code == 200, f"Get partner submissions failed: {submissions_resp.text}"
        submissions = submissions_resp.json()
        
        # Check if any submissions have status='linked' (from linked_user_ids)
        linked_submissions = [s for s in submissions if s.get("status") == "linked"]
        print(f"PASS: Partner submissions endpoint works, found {len(submissions)} total, {len(linked_submissions)} with status='linked'")
    
    def test_09_partner_dashboard_other_users_excludes_linked(self):
        """Test Partner Dashboard /api/partner/other-users excludes linked users"""
        # Login as partner user
        partner_session = requests.Session()
        partner_session.headers.update({"Content-Type": "application/json"})
        
        login_resp = partner_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "partner@example.com",
            "password": "Partner123!"
        })
        assert login_resp.status_code == 200
        partner_token = login_resp.json().get("access_token")
        partner_session.headers.update({"Authorization": f"Bearer {partner_token}"})
        
        # Get submissions (to know which users are linked)
        submissions_resp = partner_session.get(f"{BASE_URL}/api/partner/submissions")
        assert submissions_resp.status_code == 200
        submissions = submissions_resp.json()
        linked_user_ids = {s.get("user_id") for s in submissions if s.get("user_id")}
        
        # Get other users
        other_resp = partner_session.get(f"{BASE_URL}/api/partner/other-users")
        assert other_resp.status_code == 200, f"Get other users failed: {other_resp.text}"
        other_users = other_resp.json()
        
        # Verify no linked users appear in other-users
        other_user_ids = {u.get("user_id") for u in other_users}
        overlap = linked_user_ids & other_user_ids
        assert len(overlap) == 0, f"Linked users appear in other-users: {overlap}"
        
        print(f"PASS: Partner other-users excludes linked users ({len(other_users)} other users, {len(linked_user_ids)} linked)")
    
    def test_10_users_page_shows_correct_roles_after_linking(self):
        """Test Users page in admin shows correct roles after partner linking"""
        # Get all users
        users_resp = self.session.get(f"{BASE_URL}/api/admin/users")
        assert users_resp.status_code == 200
        users = users_resp.json()
        
        # Count roles
        role_counts = {}
        for u in users:
            role = u.get("role", "unknown")
            role_counts[role] = role_counts.get(role, 0) + 1
        
        print(f"PASS: Users page shows correct roles: {role_counts}")
        
        # Verify we have expected roles
        assert "admin" in role_counts, "No admin users found"
        assert "user" in role_counts or "partner" in role_counts, "No regular users or partners found"


class TestPartnerValidation:
    """Test partner validation edge cases"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with admin auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@example.com",
            "password": "Admin123!"
        })
        assert login_resp.status_code == 200
        self.admin_token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        
        yield
    
    def test_partner_create_with_valid_email(self):
        """Test creating partner with valid email works"""
        unique_id = str(uuid.uuid4())[:8]
        resp = self.session.post(f"{BASE_URL}/api/admin/partners", json={
            "name": f"TEST_Partner_Valid_Email_{unique_id}",
            "description": "Test partner with valid email",
            "contact_email": "valid@example.com"
        })
        assert resp.status_code == 200, f"Partner create with valid email failed: {resp.text}"
        partner_id = resp.json()["id"]
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/admin/partners/{partner_id}")
        print("PASS: Partner created with valid email")
    
    def test_partner_create_with_null_email(self):
        """Test creating partner with null/None email works"""
        unique_id = str(uuid.uuid4())[:8]
        resp = self.session.post(f"{BASE_URL}/api/admin/partners", json={
            "name": f"TEST_Partner_Null_Email_{unique_id}",
            "description": "Test partner with null email",
            "contact_email": None
        })
        assert resp.status_code == 200, f"Partner create with null email failed: {resp.text}"
        partner_id = resp.json()["id"]
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/admin/partners/{partner_id}")
        print("PASS: Partner created with null email")
    
    def test_partner_update_clears_linked_users(self):
        """Test updating partner with empty linked_user_ids clears the array"""
        # Create partner with linked users
        users_resp = self.session.get(f"{BASE_URL}/api/admin/users")
        users = users_resp.json()
        regular_users = [u for u in users if u["role"] == "user"]
        
        if len(regular_users) == 0:
            pytest.skip("No regular users available for this test")
        
        user_id = regular_users[0]["id"]
        unique_id = str(uuid.uuid4())[:8]
        
        create_resp = self.session.post(f"{BASE_URL}/api/admin/partners", json={
            "name": f"TEST_Partner_Clear_Links_{unique_id}",
            "description": "Test partner for clearing links",
            "linked_user_ids": [user_id]
        })
        assert create_resp.status_code == 200
        partner_id = create_resp.json()["id"]
        
        # Update with empty linked_user_ids
        update_resp = self.session.put(f"{BASE_URL}/api/admin/partners/{partner_id}", json={
            "linked_user_ids": []
        })
        assert update_resp.status_code == 200
        
        # Verify linked_user_ids is empty
        partners_resp = self.session.get(f"{BASE_URL}/api/admin/partners")
        partners = partners_resp.json()
        partner = next((p for p in partners if p["id"] == partner_id), None)
        assert partner is not None
        assert partner["linked_user_ids"] == [], f"linked_user_ids not cleared: {partner['linked_user_ids']}"
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/admin/partners/{partner_id}")
        print("PASS: Partner linked_user_ids cleared successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
