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
        self.run_test("Admin Get Users", "GET", "admin/users", 200)
        self.run_test("Admin Get Steps", "GET", "admin/steps", 200)
        self.run_test("Admin Get Partners", "GET", "admin/partners", 200)
        
        # Test new analytics endpoint
        self.run_test("Admin Get Analytics", "GET", "admin/analytics", 200)
        
        # Test user search functionality
        self.run_test("Admin Search Users (empty query)", "GET", "admin/users/search", 200)
        self.run_test("Admin Search Users (by role)", "GET", "admin/users/search?role=admin", 200)
        self.run_test("Admin Search Users (by query)", "GET", "admin/users/search?q=admin", 200)

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
        self.test_admin_endpoints()
        
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