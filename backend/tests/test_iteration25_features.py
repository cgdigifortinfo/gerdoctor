"""
Test iteration 25 features:
1. CREATE USER BUG FIX: Partner role selection no longer crashes (value='none' sentinel fix)
2. CREATE USER: User creation with role=partner and partner_id works correctly
3. CREATE USER: User creation with role=user works correctly
4. PARTNER DIALOG SEARCH: Search field filters users by name or email
5. PARTNER DIALOG LINKED: Checked users appear at top of list
6. PARTNER DIALOG LINKED: Unlinking user changes role from partner to user
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin123!"
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


class TestCreateUserWithRole:
    """Tests for POST /api/admin/users with different roles"""
    
    def test_create_user_with_role_user(self, admin_session):
        """Admin can create a user with role=user (no partner)"""
        unique_email = f"TEST_user_{uuid.uuid4().hex[:8]}@test.com"
        
        resp = admin_session.post(f"{BASE_URL}/api/admin/users", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "TEST User Role",
            "role": "user"
        })
        
        assert resp.status_code == 200, f"Create user failed: {resp.text}"
        data = resp.json()
        assert "id" in data
        assert data.get("message") == "User created"
        
        # Verify user exists with correct role
        users_resp = admin_session.get(f"{BASE_URL}/api/admin/users")
        assert users_resp.status_code == 200
        users = users_resp.json()
        created_user = next((u for u in users if u["email"] == unique_email), None)
        assert created_user is not None, "Created user not found"
        assert created_user["role"] == "user", f"Expected role 'user', got {created_user['role']}"
        print(f"✓ Created user with role=user: {unique_email}")
    
    def test_create_user_with_role_partner_and_partner_id(self, admin_session):
        """Admin can create a user with role=partner and assign to a partner org"""
        unique_email = f"TEST_partner_{uuid.uuid4().hex[:8]}@test.com"
        
        # Get a partner ID first
        partners_resp = admin_session.get(f"{BASE_URL}/api/admin/partners")
        assert partners_resp.status_code == 200
        partners = partners_resp.json()
        if not partners:
            pytest.skip("No partners available to test partner role assignment")
        
        partner_id = partners[0]["id"]
        partner_name = partners[0]["name"]
        
        resp = admin_session.post(f"{BASE_URL}/api/admin/users", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "TEST Partner Role User",
            "role": "partner",
            "partner_id": partner_id
        })
        
        assert resp.status_code == 200, f"Create partner user failed: {resp.text}"
        data = resp.json()
        assert "id" in data
        
        # Verify user exists with correct role
        users_resp = admin_session.get(f"{BASE_URL}/api/admin/users")
        users = users_resp.json()
        created_user = next((u for u in users if u["email"] == unique_email), None)
        assert created_user is not None, "Created partner user not found"
        assert created_user["role"] == "partner", f"Expected role 'partner', got {created_user['role']}"
        print(f"✓ Created user with role=partner assigned to {partner_name}: {unique_email}")
    
    def test_create_user_with_role_partner_no_partner_id(self, admin_session):
        """Admin can create a user with role=partner without assigning to a partner org"""
        unique_email = f"TEST_partner_noorg_{uuid.uuid4().hex[:8]}@test.com"
        
        resp = admin_session.post(f"{BASE_URL}/api/admin/users", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "TEST Partner No Org",
            "role": "partner"
            # No partner_id - should still work
        })
        
        assert resp.status_code == 200, f"Create partner user without org failed: {resp.text}"
        data = resp.json()
        assert "id" in data
        print(f"✓ Created user with role=partner (no org): {unique_email}")


class TestPartnerLinkedUsersEnhancements:
    """Tests for partner dialog linked users enhancements"""
    
    def test_partner_has_linked_users_array(self, admin_session):
        """GET /api/admin/partners returns linked_users array for each partner"""
        resp = admin_session.get(f"{BASE_URL}/api/admin/partners")
        assert resp.status_code == 200
        partners = resp.json()
        
        assert isinstance(partners, list)
        assert len(partners) > 0, "No partners found"
        
        for partner in partners:
            assert "linked_users" in partner, f"Partner {partner['name']} missing linked_users field"
            assert isinstance(partner["linked_users"], list)
            print(f"✓ Partner '{partner['name']}' has {len(partner['linked_users'])} linked users")
    
    def test_ils_partner_has_linked_user(self, admin_session):
        """ILS partner should have partner@example.com (ILS Admin) linked"""
        resp = admin_session.get(f"{BASE_URL}/api/admin/partners")
        assert resp.status_code == 200
        partners = resp.json()
        
        # Find ILS partner
        ils_partner = next((p for p in partners if "ILS" in p["name"]), None)
        if not ils_partner:
            pytest.skip("ILS partner not found")
        
        linked_emails = [u["email"] for u in ils_partner.get("linked_users", [])]
        print(f"ILS partner linked users: {linked_emails}")
        
        # Check if partner@example.com is linked
        assert PARTNER_EMAIL in linked_emails, f"Expected {PARTNER_EMAIL} to be linked to ILS partner"
        print(f"✓ ILS partner has {PARTNER_EMAIL} linked")
    
    def test_unlink_user_changes_role_to_user(self, admin_session):
        """Unlinking a user from partner changes their role from partner to user"""
        # First, create a test user and link them to a partner
        unique_email = f"TEST_unlink_{uuid.uuid4().hex[:8]}@test.com"
        
        # Create user with role=user
        create_resp = admin_session.post(f"{BASE_URL}/api/admin/users", json={
            "email": unique_email,
            "password": "TestPass123!",
            "name": "TEST Unlink User",
            "role": "user"
        })
        assert create_resp.status_code == 200
        user_id = create_resp.json()["id"]
        
        # Get a partner
        partners_resp = admin_session.get(f"{BASE_URL}/api/admin/partners")
        partners = partners_resp.json()
        if not partners:
            pytest.skip("No partners available")
        
        partner = partners[0]
        partner_id = partner["id"]
        existing_linked_ids = [u["id"] for u in partner.get("linked_users", [])]
        
        # Link the user to partner
        link_resp = admin_session.put(f"{BASE_URL}/api/admin/partners/{partner_id}", json={
            "linked_user_ids": existing_linked_ids + [user_id]
        })
        assert link_resp.status_code == 200
        
        # Verify user role changed to partner
        user_resp = admin_session.get(f"{BASE_URL}/api/admin/users/{user_id}")
        assert user_resp.status_code == 200
        assert user_resp.json()["role"] == "partner", "User role should be 'partner' after linking"
        print(f"✓ User role changed to 'partner' after linking")
        
        # Now unlink the user
        unlink_resp = admin_session.put(f"{BASE_URL}/api/admin/partners/{partner_id}", json={
            "linked_user_ids": existing_linked_ids  # Remove the test user
        })
        assert unlink_resp.status_code == 200
        
        # Verify user role changed back to user
        user_resp2 = admin_session.get(f"{BASE_URL}/api/admin/users/{user_id}")
        assert user_resp2.status_code == 200
        assert user_resp2.json()["role"] == "user", "User role should be 'user' after unlinking"
        print(f"✓ User role changed back to 'user' after unlinking")


class TestCodeReview:
    """Code review tests for the bug fix"""
    
    def test_create_user_dialog_uses_none_sentinel(self):
        """Verify CreateUserDialog uses value='none' instead of empty string"""
        import subprocess
        
        # Check for value="none" in SelectItem
        result = subprocess.run(
            ["grep", "-n", 'value="none"', "/app/frontend/src/pages/AdminDashboard.js"],
            capture_output=True, text=True
        )
        assert 'value="none"' in result.stdout, "CreateUserDialog should use value='none' as sentinel"
        print(f"✓ Found value='none' sentinel in code")
        
        # Check for 'Kein Partner' text
        result2 = subprocess.run(
            ["grep", "-n", 'Kein Partner', "/app/frontend/src/pages/AdminDashboard.js"],
            capture_output=True, text=True
        )
        assert 'Kein Partner' in result2.stdout, "Should have 'Kein Partner' option"
        print(f"✓ Found 'Kein Partner' option in code")
    
    def test_partner_dialog_has_user_search(self):
        """Verify PartnerDialog has user search field with correct data-testid"""
        import subprocess
        
        result = subprocess.run(
            ["grep", "-n", 'partner-user-search', "/app/frontend/src/pages/AdminDashboard.js"],
            capture_output=True, text=True
        )
        assert 'partner-user-search' in result.stdout, "PartnerDialog should have partner-user-search data-testid"
        print(f"✓ Found partner-user-search data-testid")
        
        # Check for 'Nutzer suchen...' placeholder
        result2 = subprocess.run(
            ["grep", "-n", 'Nutzer suchen', "/app/frontend/src/pages/AdminDashboard.js"],
            capture_output=True, text=True
        )
        assert 'Nutzer suchen' in result2.stdout, "Should have 'Nutzer suchen...' placeholder"
        print(f"✓ Found 'Nutzer suchen...' placeholder")
    
    def test_partner_dialog_sorts_checked_users_first(self):
        """Verify PartnerDialog sorts checked users to top"""
        import subprocess
        
        # Check for sorting logic
        result = subprocess.run(
            ["grep", "-n", 'aChecked.*bChecked', "/app/frontend/src/pages/AdminDashboard.js"],
            capture_output=True, text=True
        )
        assert 'aChecked' in result.stdout and 'bChecked' in result.stdout, "Should have sorting logic for checked users"
        print(f"✓ Found sorting logic for checked users first")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
