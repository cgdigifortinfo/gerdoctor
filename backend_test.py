#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

class GERdoctorAPITester:
    def __init__(self, base_url="https://guided-journey-5.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.session = requests.Session()
        self.admin_token = None
        self.demo_token = None
        self.partner_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
            self.failed_tests.append(f"{name}: {details}")

    def make_request(self, method, endpoint, data=None, headers=None, expected_status=200):
        """Make HTTP request and return response"""
        url = f"{self.base_url}{endpoint}"
        default_headers = {'Content-Type': 'application/json'}
        if headers:
            default_headers.update(headers)
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=default_headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=default_headers)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=default_headers)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=default_headers)
            
            return response
        except Exception as e:
            print(f"Request failed: {str(e)}")
            return None

    def test_admin_login(self):
        """Test admin login with seeded credentials"""
        print("\n🔐 Testing Admin Login...")
        response = self.make_request('POST', '/auth/login', {
            'email': 'admin@example.com',
            'password': 'Admin123!'
        })
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get('role') == 'admin':
                self.log_test("Admin login successful", True)
                # Extract token from cookies if available
                if 'access_token' in response.cookies:
                    self.admin_token = response.cookies['access_token']
                return True
            else:
                self.log_test("Admin login", False, f"Expected admin role, got {data.get('role')}")
        else:
            self.log_test("Admin login", False, f"Status: {response.status_code if response else 'No response'}")
        return False

    def test_demo_user_login(self):
        """Test demo user login"""
        print("\n👤 Testing Demo User Login...")
        response = self.make_request('POST', '/auth/login', {
            'email': 'demo@example.com',
            'password': 'Demo123!'
        })
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get('role') == 'user':
                self.log_test("Demo user login successful", True)
                return True
            else:
                self.log_test("Demo user login", False, f"Expected user role, got {data.get('role')}")
        else:
            self.log_test("Demo user login", False, f"Status: {response.status_code if response else 'No response'}")
        return False

    def test_partner_login(self):
        """Test partner login"""
        print("\n🏢 Testing Partner Login...")
        response = self.make_request('POST', '/auth/login', {
            'email': 'partner@example.com',
            'password': 'Partner123!'
        })
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get('role') == 'partner':
                self.log_test("Partner login successful", True)
                return True
            else:
                self.log_test("Partner login", False, f"Expected partner role, got {data.get('role')}")
        else:
            self.log_test("Partner login", False, f"Status: {response.status_code if response else 'No response'}")
        return False

    def test_admin_steps_endpoint(self):
        """Test admin steps endpoint returns 8 German steps"""
        print("\n📋 Testing Admin Steps Endpoint...")
        # Re-login as admin to ensure session is active
        self.make_request('POST', '/auth/login', {
            'email': 'admin@example.com',
            'password': 'Admin123!'
        })
        response = self.make_request('GET', '/admin/steps')
        
        if response and response.status_code == 200:
            steps = response.json()
            if len(steps) == 8:
                self.log_test("Admin steps count (8)", True)
                
                # Check for specific German step titles
                expected_titles = [
                    "Persönliche Daten",
                    "Service Antragstellung", 
                    "Meilenstein Antragstellung",
                    "FaMed",
                    "Service Kenntnisprüfung",
                    "Meilenstein Kenntnisprüfung", 
                    "Service Weiterbildung",
                    "Meilenstein Job finden"
                ]
                
                actual_titles = [step.get('title', '') for step in steps]
                missing_titles = [title for title in expected_titles if title not in actual_titles]
                
                if not missing_titles:
                    self.log_test("German step titles present", True)
                else:
                    self.log_test("German step titles", False, f"Missing: {missing_titles}")
                
                # Check step types
                step_types = [step.get('step_type') for step in steps]
                expected_types = ['form', 'partner_selection', 'milestone', 'display', 'partner_selection', 'milestone', 'partner_selection', 'display']
                
                if step_types == expected_types:
                    self.log_test("Step types correct", True)
                else:
                    self.log_test("Step types", False, f"Expected: {expected_types}, Got: {step_types}")
                
                # Check filter tags
                filter_tags = [step.get('filter_tag', '') for step in steps]
                expected_tags = ['', 'Antragstellung', '', '', 'Kenntnisprüfung', '', 'Weiterbildung', '']
                
                if filter_tags == expected_tags:
                    self.log_test("Filter tags correct", True)
                else:
                    self.log_test("Filter tags", False, f"Expected: {expected_tags}, Got: {filter_tags}")
                    
                return True
            else:
                self.log_test("Admin steps count", False, f"Expected 8 steps, got {len(steps)}")
        else:
            self.log_test("Admin steps endpoint", False, f"Status: {response.status_code if response else 'No response'}")
        return False

    def test_admin_partners_endpoint(self):
        """Test admin partners endpoint returns 3 tagged partners"""
        print("\n🏢 Testing Admin Partners Endpoint...")
        # Re-login as admin to ensure session is active
        self.make_request('POST', '/auth/login', {
            'email': 'admin@example.com',
            'password': 'Admin123!'
        })
        response = self.make_request('GET', '/admin/partners')
        
        if response and response.status_code == 200:
            partners = response.json()
            if len(partners) == 3:
                self.log_test("Admin partners count (3)", True)
                
                # Check partner names
                partner_names = [p.get('name', '') for p in partners]
                expected_names = ['ILS', 'ILS2', 'ILS3']
                
                if all(name in partner_names for name in expected_names):
                    self.log_test("Partner names (ILS, ILS2, ILS3)", True)
                else:
                    self.log_test("Partner names", False, f"Expected: {expected_names}, Got: {partner_names}")
                
                # Check tags
                partner_tags = [p.get('tags', []) for p in partners]
                expected_tag_sets = [['Antragstellung'], ['Kenntnisprüfung'], ['Weiterbildung']]
                
                tags_correct = True
                for i, expected_tags in enumerate(expected_tag_sets):
                    if i < len(partner_tags) and partner_tags[i] != expected_tags:
                        tags_correct = False
                        break
                
                if tags_correct:
                    self.log_test("Partner tags correct", True)
                else:
                    self.log_test("Partner tags", False, f"Expected: {expected_tag_sets}, Got: {partner_tags}")
                    
                return True
            else:
                self.log_test("Admin partners count", False, f"Expected 3 partners, got {len(partners)}")
        else:
            self.log_test("Admin partners endpoint", False, f"Status: {response.status_code if response else 'No response'}")
        return False

    def test_partners_tag_filtering(self):
        """Test partner filtering by tags"""
        print("\n🏷️ Testing Partner Tag Filtering...")
        
        # Test Antragstellung tag
        response = self.make_request('GET', '/partners?tag=Antragstellung')
        if response and response.status_code == 200:
            partners = response.json()
            if len(partners) == 1 and partners[0].get('name') == 'ILS':
                self.log_test("Antragstellung tag filter (ILS only)", True)
            else:
                self.log_test("Antragstellung tag filter", False, f"Expected 1 ILS partner, got {len(partners)} partners")
        else:
            self.log_test("Antragstellung tag filter", False, f"Status: {response.status_code if response else 'No response'}")
        
        # Test Kenntnisprüfung tag
        response = self.make_request('GET', '/partners?tag=Kenntnisprüfung')
        if response and response.status_code == 200:
            partners = response.json()
            if len(partners) == 1 and partners[0].get('name') == 'ILS2':
                self.log_test("Kenntnisprüfung tag filter (ILS2 only)", True)
            else:
                self.log_test("Kenntnisprüfung tag filter", False, f"Expected 1 ILS2 partner, got {len(partners)} partners")
        else:
            self.log_test("Kenntnisprüfung tag filter", False, f"Status: {response.status_code if response else 'No response'}")

    def test_user_steps_endpoint(self):
        """Test user steps endpoint"""
        print("\n📝 Testing User Steps Endpoint...")
        response = self.make_request('GET', '/steps')
        
        if response and response.status_code == 200:
            steps = response.json()
            if len(steps) == 8:
                self.log_test("User steps count (8)", True)
                
                # Check first step has form fields
                first_step = steps[0] if steps else {}
                if first_step.get('title') == 'Persönliche Daten':
                    self.log_test("First step is Persönliche Daten", True)
                    
                    fields = first_step.get('fields', [])
                    field_names = [f.get('name') for f in fields]
                    expected_fields = ['name', 'first_name', 'phone', 'address', 'field_of_study', 'documents']
                    
                    if all(field in field_names for field in expected_fields):
                        self.log_test("First step has required fields", True)
                        
                        # Check selectbox field
                        field_of_study = next((f for f in fields if f.get('name') == 'field_of_study'), None)
                        if field_of_study and field_of_study.get('field_type') == 'selectbox':
                            options = field_of_study.get('options', [])
                            expected_options = ['Allgemeinmedizin', 'Zahnmedizin', 'HNO']
                            if options == expected_options:
                                self.log_test("Fachgebiet selectbox options correct", True)
                            else:
                                self.log_test("Fachgebiet selectbox options", False, f"Expected: {expected_options}, Got: {options}")
                        else:
                            self.log_test("Fachgebiet selectbox field", False, "Field not found or wrong type")
                        
                        # Check multiupload field
                        documents = next((f for f in fields if f.get('name') == 'documents'), None)
                        if documents and documents.get('field_type') == 'multiupload':
                            self.log_test("Documents multiupload field present", True)
                        else:
                            self.log_test("Documents multiupload field", False, "Field not found or wrong type")
                    else:
                        missing = [f for f in expected_fields if f not in field_names]
                        self.log_test("First step fields", False, f"Missing fields: {missing}")
                else:
                    self.log_test("First step title", False, f"Expected 'Persönliche Daten', got '{first_step.get('title')}'")
                    
                return True
            else:
                self.log_test("User steps count", False, f"Expected 8 steps, got {len(steps)}")
        else:
            self.log_test("User steps endpoint", False, f"Status: {response.status_code if response else 'No response'}")
        return False

    def test_cms_content(self):
        """Test German CMS content"""
        print("\n🌐 Testing German CMS Content...")
        
        response = self.make_request('GET', '/cms/home')
        if response and response.status_code == 200:
            content = response.json().get('content', {})
            hero_title = content.get('hero_title', '')
            if 'GERdoctor' in hero_title and 'Deutschland' in hero_title:
                self.log_test("German CMS home content", True)
            else:
                self.log_test("German CMS home content", False, f"Hero title: {hero_title}")
        else:
            self.log_test("CMS home endpoint", False, f"Status: {response.status_code if response else 'No response'}")

    def test_user_registration_progress(self):
        """Test that fresh registration creates 8 pending progress entries"""
        print("\n📊 Testing User Registration Progress...")
        
        # Create a test user
        test_email = f"test_{datetime.now().strftime('%H%M%S')}@example.com"
        response = self.make_request('POST', '/auth/register', {
            'email': test_email,
            'password': 'Test123!',
            'name': 'Test User'
        })
        
        if response and response.status_code == 200:
            self.log_test("Test user registration", True)
            
            # Check progress
            progress_response = self.make_request('GET', '/steps/progress')
            if progress_response and progress_response.status_code == 200:
                progress = progress_response.json()
                if len(progress) == 8:
                    self.log_test("Fresh user has 8 progress entries", True)
                    
                    # Check all are pending
                    pending_count = sum(1 for p in progress if p.get('status') == 'pending')
                    if pending_count == 8:
                        self.log_test("All progress entries are pending", True)
                    else:
                        self.log_test("Progress entries status", False, f"Expected 8 pending, got {pending_count}")
                else:
                    self.log_test("Fresh user progress count", False, f"Expected 8 entries, got {len(progress)}")
            else:
                self.log_test("User progress endpoint", False, f"Status: {progress_response.status_code if progress_response else 'No response'}")
        else:
            self.log_test("Test user registration", False, f"Status: {response.status_code if response else 'No response'}")

    def run_all_tests(self):
        """Run all tests"""
        print("🧪 Starting GERdoctor API Tests...")
        print("=" * 50)
        
        # Authentication tests
        admin_login_ok = self.test_admin_login()
        demo_login_ok = self.test_demo_user_login()
        partner_login_ok = self.test_partner_login()
        
        # Admin endpoint tests
        if admin_login_ok:
            self.test_admin_steps_endpoint()
            self.test_admin_partners_endpoint()
        
        # Public endpoint tests
        self.test_partners_tag_filtering()
        self.test_user_steps_endpoint()
        self.test_cms_content()
        
        # User registration test
        if demo_login_ok:
            self.test_user_registration_progress()
        
        # Print summary
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.failed_tests:
            print("\n❌ Failed Tests:")
            for failure in self.failed_tests:
                print(f"  - {failure}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = GERdoctorAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())