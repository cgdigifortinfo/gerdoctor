#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

class GermanMedicalAppTester:
    def __init__(self, base_url="https://guided-journey-5.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.tests_run = 0
        self.tests_passed = 0
        self.admin_user = None
        self.demo_user = None

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
            if details:
                print(f"   {details}")
        else:
            print(f"❌ {name}")
            if details:
                print(f"   {details}")

    def login_user(self, email, password):
        """Login and return user data"""
        try:
            response = self.session.post(f"{self.base_url}/auth/login", 
                                       json={"email": email, "password": password})
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Login failed for {email}: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Login error for {email}: {str(e)}")
            return None

    def test_admin_login(self):
        """Test admin login"""
        self.admin_user = self.login_user("admin@example.com", "Admin123!")
        success = self.admin_user is not None
        self.log_test("Admin Login", success, 
                     f"Role: {self.admin_user.get('role') if self.admin_user else 'Failed'}")
        return success

    def test_demo_user_login(self):
        """Test demo user login"""
        self.demo_user = self.login_user("demo@example.com", "Demo123!")
        success = self.demo_user is not None
        self.log_test("Demo User Login", success,
                     f"Role: {self.demo_user.get('role') if self.demo_user else 'Failed'}")
        return success

    def test_steps_history_endpoint(self):
        """Test GET /api/steps/history endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/steps/history")
            success = response.status_code == 200
            
            if success:
                history = response.json()
                self.log_test("GET /api/steps/history", True, 
                             f"Returned {len(history)} history entries")
                
                # Check structure of history entries
                if history:
                    entry = history[0]
                    required_fields = ['step_title', 'action', 'timestamp', 'step_order']
                    has_required = all(field in entry for field in required_fields)
                    self.log_test("History Entry Structure", has_required,
                                 f"Fields: {list(entry.keys())}")
                else:
                    self.log_test("History Entry Structure", True, "Empty history (expected for fresh user)")
            else:
                self.log_test("GET /api/steps/history", False, 
                             f"Status: {response.status_code}, Response: {response.text}")
            
            return success
        except Exception as e:
            self.log_test("GET /api/steps/history", False, f"Exception: {str(e)}")
            return False

    def test_progress_history_creation(self):
        """Test that updating progress creates history entries"""
        try:
            # Get current steps
            steps_response = self.session.get(f"{self.base_url}/steps")
            if steps_response.status_code != 200:
                self.log_test("Progress History Creation - Get Steps", False, "Failed to get steps")
                return False
            
            steps = steps_response.json()
            if not steps:
                self.log_test("Progress History Creation", False, "No steps available")
                return False
            
            first_step = steps[0]
            
            # Get initial history count
            history_response = self.session.get(f"{self.base_url}/steps/history")
            initial_count = len(history_response.json()) if history_response.status_code == 200 else 0
            
            # Update progress to in_progress
            progress_data = {
                "step_id": first_step["id"],
                "status": "in_progress", 
                "data": {"test_field": "test_value"}
            }
            
            update_response = self.session.put(f"{self.base_url}/steps/progress", json=progress_data)
            update_success = update_response.status_code == 200
            
            if not update_success:
                self.log_test("Progress History Creation - Update Progress", False, 
                             f"Status: {update_response.status_code}, Response: {update_response.text}")
                return False
            
            # Check if history entry was created
            new_history_response = self.session.get(f"{self.base_url}/steps/history")
            if new_history_response.status_code == 200:
                new_history = new_history_response.json()
                new_count = len(new_history)
                
                history_created = new_count > initial_count
                self.log_test("Progress History Creation", history_created,
                             f"History entries: {initial_count} -> {new_count}")
                
                if history_created and new_history:
                    latest_entry = new_history[0]  # Should be most recent
                    correct_step = latest_entry.get('step_title') == first_step['title']
                    correct_action = latest_entry.get('action') == 'in_progress'
                    
                    self.log_test("History Entry Content", correct_step and correct_action,
                                 f"Step: {latest_entry.get('step_title')}, Action: {latest_entry.get('action')}")
                
                return history_created
            else:
                self.log_test("Progress History Creation - Get New History", False, 
                             f"Status: {new_history_response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Progress History Creation", False, f"Exception: {str(e)}")
            return False

    def test_admin_steps_endpoint(self):
        """Test admin steps endpoint to verify condition presets structure"""
        try:
            # Login as admin first
            if not self.admin_user:
                if not self.test_admin_login():
                    return False
            
            response = self.session.get(f"{self.base_url}/admin/steps")
            success = response.status_code == 200
            
            if success:
                steps = response.json()
                self.log_test("GET /api/admin/steps", True, f"Retrieved {len(steps)} steps")
                
                # Check if steps have conditions field (for presets)
                steps_with_conditions = [s for s in steps if 'conditions' in s]
                self.log_test("Steps with Conditions Field", len(steps_with_conditions) > 0,
                             f"{len(steps_with_conditions)} steps have conditions field")
                
                return True
            else:
                self.log_test("GET /api/admin/steps", False, 
                             f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("GET /api/admin/steps", False, f"Exception: {str(e)}")
            return False

    def test_step_all_data_endpoint(self):
        """Test /api/steps/all-data endpoint for conditional logic"""
        try:
            response = self.session.get(f"{self.base_url}/steps/all-data")
            success = response.status_code == 200
            
            if success:
                all_data = response.json()
                self.log_test("GET /api/steps/all-data", True, f"Retrieved data for {len(all_data)} steps")
                
                if all_data:
                    first_step = all_data[0]
                    required_fields = ['step_id', 'order', 'title', 'step_type', 'status', 'data', 'conditions']
                    has_required = all(field in first_step for field in required_fields)
                    self.log_test("All-Data Structure", has_required,
                                 f"Fields: {list(first_step.keys())}")
                
                return True
            else:
                self.log_test("GET /api/steps/all-data", False,
                             f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("GET /api/steps/all-data", False, f"Exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all backend tests"""
        print("🧪 Starting German Medical Onboarding App Backend Tests (Iteration 11)")
        print("=" * 70)
        
        # Test authentication
        print("\n📋 Authentication Tests:")
        admin_login_ok = self.test_admin_login()
        demo_login_ok = self.test_demo_user_login()
        
        if not demo_login_ok:
            print("❌ Cannot proceed with user tests - demo login failed")
            return False
        
        # Test new history functionality
        print("\n📋 Progress History Tests:")
        self.test_steps_history_endpoint()
        self.test_progress_history_creation()
        
        # Test step data endpoints
        print("\n📋 Step Data Tests:")
        self.test_step_all_data_endpoint()
        
        # Test admin endpoints if admin login worked
        if admin_login_ok:
            print("\n📋 Admin Tests:")
            self.test_admin_steps_endpoint()
        
        # Summary
        print("\n" + "=" * 70)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        return self.tests_passed == self.tests_run

def main():
    tester = GermanMedicalAppTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())