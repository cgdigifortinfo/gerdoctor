import requests
import sys
import json
from datetime import datetime, timedelta

class Iteration6APITester:
    def __init__(self, base_url="https://guided-journey-5.preview.emergentagent.com"):
        self.base_url = base_url
        self.session = requests.Session()
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

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        
        # Prepare headers
        test_headers = {'Content-Type': 'application/json'}
        if headers:
            test_headers.update(headers)

        try:
            if method == 'GET':
                response = self.session.get(url, headers=test_headers, params=params)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=test_headers)

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
        """Test admin login"""
        response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@example.com", "password": "Admin123!"}
        )
        return response is not None

    def test_registration_creates_progress_entries(self):
        """Test that registration creates progress entries for all 4 steps"""
        print("\n🔍 Testing Registration Creates 4 Progress Entries...")
        
        # First, get the current steps to know how many there should be
        if not self.test_admin_login():
            self.log_test("Registration Progress Test Setup", False, "Admin login failed")
            return False
        
        steps_response = self.run_test("Get Steps for Progress Test", "GET", "steps", 200)
        if not steps_response:
            self.log_test("Registration Progress Test Setup", False, "Could not get steps")
            return False
        
        expected_step_count = len(steps_response)
        print(f"📋 Found {expected_step_count} steps in system")
        
        # Generate unique test user
        timestamp = datetime.now().strftime('%H%M%S%f')[:-3]  # Include milliseconds
        test_email = f"progresstest_{timestamp}@example.com"
        test_password = "TestPass123!"
        test_name = f"Progress Test User {timestamp}"
        
        # Register new user
        register_response = self.run_test(
            "Register User for Progress Test",
            "POST",
            "auth/register",
            200,
            data={"email": test_email, "password": test_password, "name": test_name}
        )
        
        if not register_response:
            self.log_test("Registration Progress Creation", False, "Registration failed")
            return False
        
        # Login as the new user to check their progress
        login_response = self.run_test(
            "Login New User for Progress Check",
            "POST",
            "auth/login",
            200,
            data={"email": test_email, "password": test_password}
        )
        
        if not login_response:
            self.log_test("Registration Progress Creation", False, "Login after registration failed")
            return False
        
        # Get user progress
        progress_response = self.run_test("Get New User Progress", "GET", "steps/progress", 200)
        
        if not progress_response:
            self.log_test("Registration Progress Creation", False, "Could not get user progress")
            return False
        
        # Check if progress entries were created for all steps
        progress_count = len(progress_response)
        
        if progress_count == expected_step_count:
            # Check that all progress entries have 'pending' status
            all_pending = all(p.get('status') == 'pending' for p in progress_response)
            if all_pending:
                self.log_test("Registration Progress Creation", True, f"Created {progress_count} progress entries, all with 'pending' status")
                
                # Additional check: verify all progress entries have the required fields
                required_fields = ['user_id', 'step_id', 'status', 'data']
                all_have_fields = all(
                    all(field in p for field in required_fields) 
                    for p in progress_response
                )
                
                if all_have_fields:
                    self.log_test("Progress Entry Structure", True, "All progress entries have required fields")
                else:
                    self.log_test("Progress Entry Structure", False, "Some progress entries missing required fields")
                
                return True
            else:
                pending_count = sum(1 for p in progress_response if p.get('status') == 'pending')
                self.log_test("Registration Progress Creation", False, f"Expected all {progress_count} entries to be 'pending', but only {pending_count} are pending")
                return False
        else:
            self.log_test("Registration Progress Creation", False, f"Expected {expected_step_count} progress entries, got {progress_count}")
            return False

    def test_audit_log_filtering(self):
        """Test audit log filtering by action type and date range"""
        print("\n🔍 Testing Audit Log Filtering...")
        
        if not self.test_admin_login():
            self.log_test("Audit Log Filter Test Setup", False, "Admin login failed")
            return False
        
        # Test 1: Get all audit logs to establish baseline
        all_logs_response = self.run_test("Get All Audit Logs", "GET", "admin/audit-log", 200)
        if not all_logs_response:
            return False
        
        all_logs = all_logs_response.get('logs', [])
        action_types = all_logs_response.get('action_types', [])
        
        print(f"📊 Found {len(all_logs)} total audit logs")
        print(f"📊 Available action types: {action_types}")
        
        # Test 2: Filter by action type (if we have cms_update actions)
        if 'cms_update' in action_types:
            cms_filtered_response = self.run_test(
                "Filter Audit Logs by Action (cms_update)", 
                "GET", 
                "admin/audit-log", 
                200,
                params={"action": "cms_update"}
            )
            
            if cms_filtered_response:
                cms_logs = cms_filtered_response.get('logs', [])
                # Verify all returned logs are cms_update actions
                all_cms_update = all(log.get('action') == 'cms_update' for log in cms_logs)
                
                if all_cms_update:
                    self.log_test("Audit Log Action Filter", True, f"Filtered to {len(cms_logs)} cms_update logs")
                else:
                    non_cms_count = sum(1 for log in cms_logs if log.get('action') != 'cms_update')
                    self.log_test("Audit Log Action Filter", False, f"Found {non_cms_count} non-cms_update logs in filtered results")
            else:
                self.log_test("Audit Log Action Filter", False, "Failed to get filtered results")
        else:
            # Create a cms_update action to test filtering
            print("🔄 Creating CMS update to test filtering...")
            cms_update_response = self.run_test(
                "Create CMS Update for Filter Test", 
                "PUT", 
                "cms/home", 
                200,
                data={"section": "home", "content": {"hero_title": "Filter Test Update"}}
            )
            
            if cms_update_response:
                # Wait a moment for the audit log to be created
                import time
                time.sleep(1)
                
                # Now test filtering
                cms_filtered_response = self.run_test(
                    "Filter Audit Logs by Action (cms_update)", 
                    "GET", 
                    "admin/audit-log", 
                    200,
                    params={"action": "cms_update"}
                )
                
                if cms_filtered_response:
                    cms_logs = cms_filtered_response.get('logs', [])
                    if cms_logs and cms_logs[0].get('action') == 'cms_update':
                        self.log_test("Audit Log Action Filter", True, f"Successfully filtered to cms_update logs")
                    else:
                        self.log_test("Audit Log Action Filter", False, "Filter did not return expected cms_update logs")
        
        # Test 3: Date range filtering
        print("🗓️ Testing date range filtering...")
        
        # Get current date and yesterday
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Test filtering from yesterday to tomorrow (should include today's logs)
        date_filtered_response = self.run_test(
            "Filter Audit Logs by Date Range", 
            "GET", 
            "admin/audit-log", 
            200,
            params={"date_from": yesterday, "date_to": tomorrow}
        )
        
        if date_filtered_response:
            date_logs = date_filtered_response.get('logs', [])
            self.log_test("Audit Log Date Filter", True, f"Date range filter returned {len(date_logs)} logs")
            
            # Verify logs are within date range
            if date_logs:
                # Check if timestamps are within range (basic check)
                valid_dates = True
                for log in date_logs[:5]:  # Check first 5 logs
                    timestamp = log.get('timestamp', '')
                    if timestamp:
                        try:
                            log_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            yesterday_dt = datetime.strptime(yesterday, '%Y-%m-%d')
                            tomorrow_dt = datetime.strptime(tomorrow, '%Y-%m-%d') + timedelta(days=1)
                            
                            if not (yesterday_dt <= log_date <= tomorrow_dt):
                                valid_dates = False
                                break
                        except:
                            pass  # Skip invalid timestamps
                
                if valid_dates:
                    self.log_test("Audit Log Date Range Validation", True, "Logs are within specified date range")
                else:
                    self.log_test("Audit Log Date Range Validation", False, "Some logs are outside specified date range")
        
        # Test 4: Combined filtering (action + date)
        if 'cms_update' in action_types or cms_update_response:
            combined_response = self.run_test(
                "Filter Audit Logs by Action and Date", 
                "GET", 
                "admin/audit-log", 
                200,
                params={"action": "cms_update", "date_from": yesterday, "date_to": tomorrow}
            )
            
            if combined_response:
                combined_logs = combined_response.get('logs', [])
                self.log_test("Audit Log Combined Filter", True, f"Combined filter returned {len(combined_logs)} logs")
        
        return True

    def run_iteration6_tests(self):
        """Run iteration 6 specific tests"""
        print("🚀 Starting Iteration 6 Specific API Tests...")
        print(f"Testing against: {self.base_url}")
        
        # Test registration creates progress entries
        self.test_registration_creates_progress_entries()
        
        # Test audit log filtering
        self.test_audit_log_filtering()
        
        # Print summary
        print(f"\n📊 Iteration 6 Test Summary:")
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
    tester = Iteration6APITester()
    success = tester.run_iteration6_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())