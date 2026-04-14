import requests
import sys
import json
from datetime import datetime

class GuidedJourneyAPITester:
    def __init__(self, base_url="https://guided-journey-5.preview.emergentagent.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.admin_token = None
        self.user_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
        
        self.test_results.append({
            "name": name,
            "success": success,
            "details": details
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, cookies=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        
        # Prepare headers
        test_headers = {'Content-Type': 'application/json'}
        if headers:
            test_headers.update(headers)

        try:
            if method == 'GET':
                response = self.session.get(url, headers=test_headers, cookies=cookies)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=test_headers, cookies=cookies)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=test_headers, cookies=cookies)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=test_headers, cookies=cookies)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if not success:
                try:
                    error_data = response.json()
                    details += f", Response: {error_data}"
                except:
                    details += f", Response: {response.text[:200]}"
            
            self.log_test(name, success, details)
            
            if success:
                try:
                    return response.json()
                except:
                    return {"status": "success"}
            return None

        except Exception as e:
            self.log_test(name, False, f"Error: {str(e)}")
            return None

    def test_admin_login(self):
        """Test admin login and store token"""
        print("\n🔐 Testing Admin Authentication...")
        
        response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@example.com", "password": "Admin123!"}
        )
        
        if response:
            # Check if we got cookies (httpOnly)
            if self.session.cookies:
                print("✅ Admin login successful with cookies")
                return True
            else:
                print("❌ Admin login successful but no cookies received")
                return False
        return False

    def test_user_registration_and_login(self):
        """Test user registration and login"""
        print("\n👤 Testing User Registration & Login...")
        
        # Generate unique test user
        timestamp = datetime.now().strftime('%H%M%S')
        test_email = f"testuser_{timestamp}@example.com"
        test_password = "TestPass123!"
        test_name = f"Test User {timestamp}"
        
        # Test registration
        response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data={"email": test_email, "password": test_password, "name": test_name}
        )
        
        if response:
            # Test login with new user
            login_response = self.run_test(
                "User Login",
                "POST",
                "auth/login",
                200,
                data={"email": test_email, "password": test_password}
            )
            return login_response is not None
        return False

    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n🔑 Testing Auth Endpoints...")
        
        # Test /me endpoint
        self.run_test("Get Current User", "GET", "auth/me", 200)
        
        # Test refresh token
        self.run_test("Refresh Token", "POST", "auth/refresh", 200)
        
        # Test logout
        self.run_test("Logout", "POST", "auth/logout", 200)

    def test_steps_endpoints(self):
        """Test steps endpoints"""
        print("\n📋 Testing Steps Endpoints...")
        
        # Re-login as admin for protected endpoints
        self.test_admin_login()
        
        # Test get steps
        self.run_test("Get Steps", "GET", "steps", 200)
        
        # Test get progress
        self.run_test("Get User Progress", "GET", "steps/progress", 200)

    def test_partners_endpoints(self):
        """Test partners endpoints"""
        print("\n🏢 Testing Partners Endpoints...")
        
        # Test get partners (public endpoint)
        self.run_test("Get Partners", "GET", "partners", 200)

    def test_cms_endpoints(self):
        """Test CMS endpoints"""
        print("\n📄 Testing CMS Endpoints...")
        
        # Test get CMS content
        self.run_test("Get Home Content", "GET", "cms/home", 200)
        self.run_test("Get About Content", "GET", "cms/about", 200)
        self.run_test("Get Partners Content", "GET", "cms/partners", 200)

    def test_admin_endpoints(self):
        """Test admin endpoints"""
        print("\n👑 Testing Admin Endpoints...")
        
        # Re-login as admin
        self.test_admin_login()
        
        # Test admin endpoints
        users_response = self.run_test("Admin Get Users", "GET", "admin/users", 200)
        self.run_test("Admin Get Steps", "GET", "admin/steps", 200)
        self.run_test("Admin Get Partners", "GET", "admin/partners", 200)
        
        # Test new analytics endpoint
        self.run_test("Admin Get Analytics", "GET", "admin/analytics", 200)
        
        # Test user search functionality
        self.run_test("Admin Search Users (empty query)", "GET", "admin/users/search", 200)
        self.run_test("Admin Search Users (by role)", "GET", "admin/users/search?role=admin", 200)
        self.run_test("Admin Search Users (by query)", "GET", "admin/users/search?q=admin", 200)
        
        # Test NEW FEATURES for iteration 3
        print("\n🆕 Testing New Admin Features (Iteration 3)...")
        
        # Test CSV export
        try:
            url = f"{self.base_url}/api/admin/export/users"
            response = self.session.get(url, headers={'Content-Type': 'application/json'})
            if response.status_code == 200 and 'text/csv' in response.headers.get('content-type', ''):
                self.log_test("Admin CSV Export", True, "CSV file downloaded successfully")
            else:
                self.log_test("Admin CSV Export", False, f"Status: {response.status_code}, Content-Type: {response.headers.get('content-type', 'unknown')}")
        except Exception as e:
            self.log_test("Admin CSV Export", False, f"Error: {str(e)}")
        
        # Test bulk role update (if we have users)
        if users_response and len(users_response) > 0:
            # Get first user ID for testing
            test_user_ids = [users_response[0]['id']] if users_response else []
            if test_user_ids:
                bulk_response = self.run_test(
                    "Admin Bulk Role Update", 
                    "PUT", 
                    "admin/users/bulk-role", 
                    200,
                    data={"user_ids": test_user_ids, "role": "user"}
                )
                if bulk_response:
                    print(f"✅ Bulk role update successful: {bulk_response.get('message', 'No message')}")
        else:
            self.log_test("Admin Bulk Role Update", False, "No users available for testing")

    def test_audit_log_endpoints(self):
        """Test audit log endpoints (NEW for iteration 5)"""
        print("\n📋 Testing Audit Log Endpoints (Iteration 5)...")
        
        # Re-login as admin
        self.test_admin_login()
        
        # Test get audit log
        audit_response = self.run_test("Admin Get Audit Log", "GET", "admin/audit-log", 200)
        
        if audit_response:
            logs = audit_response.get('logs', [])
            total = audit_response.get('total', 0)
            
            if isinstance(logs, list):
                self.log_test("Audit Log Structure", True, f"Found {len(logs)} logs out of {total} total")
                
                # Check if logs have required fields
                if logs:
                    first_log = logs[0]
                    required_fields = ['actor_email', 'action', 'target_type', 'timestamp']
                    missing_fields = [field for field in required_fields if field not in first_log]
                    
                    if not missing_fields:
                        self.log_test("Audit Log Fields", True, "All required fields present")
                    else:
                        self.log_test("Audit Log Fields", False, f"Missing fields: {missing_fields}")
                else:
                    self.log_test("Audit Log Content", True, "No audit logs yet (expected for new system)")
            else:
                self.log_test("Audit Log Structure", False, "Logs is not a list")
        
        # Test audit log with pagination
        self.run_test("Admin Get Audit Log (Limited)", "GET", "admin/audit-log?limit=10&skip=0", 200)
        
        # Perform an action that should create an audit log entry
        print("\n🔄 Testing Audit Log Creation...")
        
        # Update CMS content to trigger audit log
        cms_update_response = self.run_test(
            "Update CMS Content (for audit)", 
            "PUT", 
            "cms/home", 
            200,
            data={"section": "home", "content": {"hero_title": "Test Audit Log Update"}}
        )
        
        if cms_update_response:
            # Wait a moment and check if audit log was created
            import time
            time.sleep(1)
            
            # Get audit log again to see if new entry was created
            new_audit_response = self.run_test("Check New Audit Log Entry", "GET", "admin/audit-log?limit=5", 200)
            
            if new_audit_response:
                new_logs = new_audit_response.get('logs', [])
                if new_logs:
                    # Check if the most recent log is our CMS update
                    recent_log = new_logs[0]
                    if (recent_log.get('action') == 'cms_update' and 
                        recent_log.get('target_type') == 'cms' and
                        recent_log.get('actor_email') == 'admin@example.com'):
                        self.log_test("Audit Log Creation", True, "CMS update audit log created successfully")
                    else:
                        self.log_test("Audit Log Creation", False, f"Expected cms_update audit log, got: {recent_log}")
                else:
                    self.log_test("Audit Log Creation", False, "No audit logs found after CMS update")

    def test_notification_preferences(self):
        """Test notification preferences endpoints"""
        print("\n🔔 Testing Notification Preferences...")
        
        # Test get notification preferences
        prefs_response = self.run_test("Get Notification Preferences", "GET", "notifications/preferences", 200)
        
        # Test update notification preferences
        if prefs_response:
            # Update preferences
            new_prefs = {
                "email_on_step_enter": False,
                "email_on_step_edit": True,
                "email_on_step_leave": False
            }
            update_response = self.run_test(
                "Update Notification Preferences", 
                "PUT", 
                "notifications/preferences", 
                200,
                data=new_prefs
            )
            
            if update_response:
                # Verify the update by getting preferences again
                verify_response = self.run_test("Verify Updated Preferences", "GET", "notifications/preferences", 200)
                if verify_response:
                    # Check if the preferences were actually updated
                    if (verify_response.get('email_on_step_enter') == False and 
                        verify_response.get('email_on_step_edit') == True and 
                        verify_response.get('email_on_step_leave') == False):
                        self.log_test("Notification Preferences Update Verification", True, "Preferences updated correctly")
                    else:
                        self.log_test("Notification Preferences Update Verification", False, f"Preferences not updated correctly: {verify_response}")
    def test_profile_endpoints(self):
        """Test profile endpoints"""
        print("\n👤 Testing Profile Endpoints...")
        
        # Test get profile
        self.run_test("Get Profile", "GET", "profile", 200)

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Guided Journey API Tests...")
        print(f"Testing against: {self.base_url}")
        
        # Test authentication first
        if not self.test_admin_login():
            print("❌ Admin login failed, stopping critical tests")
            return False
        
        # Test user registration and login
        self.test_user_registration_and_login()
        
        # Test other endpoints
        self.test_auth_endpoints()
        self.test_steps_endpoints()
        self.test_partners_endpoints()
        self.test_cms_endpoints()
        self.test_profile_endpoints()
        self.test_notification_preferences()
        self.test_admin_endpoints()
        self.test_audit_log_endpoints()
        
        # Print summary
        print(f"\n📊 Test Summary:")
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        # Print failed tests
        failed_tests = [t for t in self.test_results if not t['success']]
        if failed_tests:
            print(f"\n❌ Failed Tests ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  - {test['name']}: {test['details']}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = GuidedJourneyAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())