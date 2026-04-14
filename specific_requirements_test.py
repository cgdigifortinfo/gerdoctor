#!/usr/bin/env python3
"""
Specific requirements test for Guided Journey App
Testing the exact requirements from the review request
"""

import requests
import sys
import json
from datetime import datetime

class SpecificRequirementsTest:
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

    def test_admin_login_and_analytics(self):
        """Test admin login and verify analytics data"""
        print("\n🔐 Testing Admin Login and Analytics...")
        
        # Test admin login
        url = f"{self.base_url}/api/auth/login"
        response = self.session.post(url, json={
            "email": "admin@example.com", 
            "password": "Admin123!"
        })
        
        if response.status_code == 200:
            self.log_test("Admin Login", True, f"Status: {response.status_code}")
            
            # Test analytics endpoint
            analytics_url = f"{self.base_url}/api/admin/analytics"
            analytics_response = self.session.get(analytics_url)
            
            if analytics_response.status_code == 200:
                analytics_data = analytics_response.json()
                
                # Check Total Users > 0
                total_users = analytics_data.get('total_users', 0)
                if total_users > 0:
                    self.log_test("Total Users > 0", True, f"Total Users: {total_users}")
                else:
                    self.log_test("Total Users > 0", False, f"Total Users: {total_users}")
                
                # Check Active Partners = 3
                total_partners = analytics_data.get('total_partners', 0)
                if total_partners == 3:
                    self.log_test("Active Partners = 3", True, f"Active Partners: {total_partners}")
                else:
                    self.log_test("Active Partners = 3", False, f"Active Partners: {total_partners}")
                
                # Check step completion rates for 4 steps
                step_analytics = analytics_data.get('step_analytics', [])
                if len(step_analytics) == 4:
                    self.log_test("4 Steps Present", True, f"Steps count: {len(step_analytics)}")
                    
                    # Check each step has completion rate
                    for i, step in enumerate(step_analytics):
                        step_title = step.get('title', f'Step {i+1}')
                        completion_rate = step.get('completion_rate', 0)
                        total = step.get('total', 0)
                        completed = step.get('completed', 0)
                        
                        self.log_test(
                            f"Step {i+1} Analytics", 
                            True, 
                            f"{step_title}: {completed}/{total} ({completion_rate}%)"
                        )
                else:
                    self.log_test("4 Steps Present", False, f"Steps count: {len(step_analytics)}")
                
                print(f"\n📊 Analytics Summary:")
                print(f"   Total Users: {analytics_data.get('total_users', 0)}")
                print(f"   Active Partners: {analytics_data.get('total_partners', 0)}")
                print(f"   Admin Count: {analytics_data.get('admin_count', 0)}")
                print(f"   Partner Count: {analytics_data.get('partner_count', 0)}")
                print(f"   Recent Registrations: {analytics_data.get('recent_registrations', 0)}")
                
            else:
                self.log_test("Admin Analytics", False, f"Status: {analytics_response.status_code}")
        else:
            self.log_test("Admin Login", False, f"Status: {response.status_code}")

    def test_demo_user_login_and_progress(self):
        """Test demo user login and verify 0% progress"""
        print("\n👤 Testing Demo User Login and Progress...")
        
        # Create new session for demo user
        demo_session = requests.Session()
        
        # Test demo user login
        url = f"{self.base_url}/api/auth/login"
        response = demo_session.post(url, json={
            "email": "demo@example.com", 
            "password": "Demo123!"
        })
        
        if response.status_code == 200:
            user_data = response.json()
            self.log_test("Demo User Login", True, f"User: {user_data.get('name', 'Unknown')}")
            
            # Test user progress
            progress_url = f"{self.base_url}/api/steps/progress"
            progress_response = demo_session.get(progress_url)
            
            if progress_response.status_code == 200:
                progress_data = progress_response.json()
                
                # Calculate progress percentage
                completed_count = sum(1 for p in progress_data if p.get('status') == 'completed')
                total_count = len(progress_data)
                progress_percentage = (completed_count / total_count * 100) if total_count > 0 else 0
                
                if progress_percentage == 0:
                    self.log_test("Demo User 0% Progress", True, f"Progress: {progress_percentage}%")
                else:
                    self.log_test("Demo User 0% Progress", False, f"Progress: {progress_percentage}%")
                
                # Check first step is active (pending or in_progress)
                if progress_data:
                    first_step = progress_data[0]
                    first_step_status = first_step.get('status', 'unknown')
                    if first_step_status in ['pending', 'in_progress']:
                        self.log_test("First Step Active", True, f"Status: {first_step_status}")
                    else:
                        self.log_test("First Step Active", False, f"Status: {first_step_status}")
                
                print(f"\n📈 Demo User Progress:")
                print(f"   Total Steps: {total_count}")
                print(f"   Completed: {completed_count}")
                print(f"   Progress: {progress_percentage}%")
                
            else:
                self.log_test("Demo User Progress", False, f"Status: {progress_response.status_code}")
        else:
            self.log_test("Demo User Login", False, f"Status: {response.status_code}")

    def test_seeded_partners(self):
        """Test that 3 specific partners are seeded"""
        print("\n🏢 Testing Seeded Partners...")
        
        url = f"{self.base_url}/api/partners"
        response = self.session.get(url)
        
        if response.status_code == 200:
            partners = response.json()
            
            expected_partners = ["TechVenture", "Global Consulting", "Innovation Labs"]
            found_partners = []
            
            for partner in partners:
                partner_name = partner.get('name', '')
                for expected in expected_partners:
                    if expected in partner_name:
                        found_partners.append(expected)
                        break
            
            if len(found_partners) == 3:
                self.log_test("3 Seeded Partners", True, f"Found: {found_partners}")
            else:
                self.log_test("3 Seeded Partners", False, f"Found: {found_partners}, Expected: {expected_partners}")
            
            print(f"\n🏢 Partners Found:")
            for partner in partners:
                print(f"   - {partner.get('name', 'Unknown')} ({partner.get('category', 'No category')})")
                
        else:
            self.log_test("Get Partners", False, f"Status: {response.status_code}")

    def test_seeded_steps(self):
        """Test that 4 steps are seeded"""
        print("\n📋 Testing Seeded Steps...")
        
        # Re-login as admin
        url = f"{self.base_url}/api/auth/login"
        self.session.post(url, json={"email": "admin@example.com", "password": "Admin123!"})
        
        steps_url = f"{self.base_url}/api/admin/steps"
        response = self.session.get(steps_url)
        
        if response.status_code == 200:
            steps = response.json()
            
            if len(steps) == 4:
                self.log_test("4 Seeded Steps", True, f"Steps count: {len(steps)}")
                
                expected_step_titles = ["Complete Your Profile", "Select a Partner", "Partner Application", "Review & Confirm"]
                found_titles = []
                
                for step in sorted(steps, key=lambda x: x.get('order', 0)):
                    step_title = step.get('title', '')
                    found_titles.append(step_title)
                
                print(f"\n📋 Steps Found:")
                for i, title in enumerate(found_titles):
                    print(f"   {i+1}. {title}")
                
                # Check if we have the expected step types
                step_types = [step.get('step_type') for step in steps]
                if 'form' in step_types and 'partner_selection' in step_types and 'info' in step_types:
                    self.log_test("Step Types Variety", True, f"Types: {set(step_types)}")
                else:
                    self.log_test("Step Types Variety", False, f"Types: {set(step_types)}")
                    
            else:
                self.log_test("4 Seeded Steps", False, f"Steps count: {len(steps)}")
        else:
            self.log_test("Get Admin Steps", False, f"Status: {response.status_code}")

    def test_cms_content(self):
        """Test CMS content is seeded"""
        print("\n📄 Testing CMS Content...")
        
        sections = ['home', 'about', 'partners']
        
        for section in sections:
            url = f"{self.base_url}/api/cms/{section}"
            response = self.session.get(url)
            
            if response.status_code == 200:
                content = response.json()
                content_data = content.get('content', {})
                
                if content_data:
                    self.log_test(f"CMS {section.title()} Content", True, f"Keys: {list(content_data.keys())}")
                else:
                    self.log_test(f"CMS {section.title()} Content", False, "No content found")
            else:
                self.log_test(f"CMS {section.title()} Content", False, f"Status: {response.status_code}")

    def run_all_tests(self):
        """Run all specific requirement tests"""
        print("🎯 Testing Specific Requirements for Guided Journey App...")
        print(f"Testing against: {self.base_url}")
        
        self.test_admin_login_and_analytics()
        self.test_demo_user_login_and_progress()
        self.test_seeded_partners()
        self.test_seeded_steps()
        self.test_cms_content()
        
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
        else:
            print(f"\n🎉 All specific requirements tests passed!")
        
        return self.tests_passed == self.tests_run

def main():
    tester = SpecificRequirementsTest()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())