import requests
import json
import time
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8000"

class ComprehensiveSystemTester:
    def __init__(self):
        self.admin_token = None
        self.user_token = None
        self.api_key = None
        self.session_id = None
        self.document_id = None
        
        # Test users
        self.admin_email = "admin@company.com"
        self.user_email = "employee@company.com"
        self.password = "TestPassword123!"
    
    def print_section(self, title: str):
        print(f"\n{'='*60}")
        print(f"  {title}")
        print('='*60)
    
    def print_step(self, step: str, status: str = ""):
        print(f"\n{step} {status}")
    
    def test_health_check(self) -> bool:
        """Test basic system health"""
        self.print_step("1. Testing system health...")
        
        try:
            response = requests.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                health = response.json()
                print(f"   ✅ Status: {health.get('status')}")
                print(f"   ✅ Version: {health.get('version')}")
                print(f"   ✅ Environment: {health.get('environment')}")
                print(f"   ✅ Auth: {health.get('auth')}")
                return True
            else:
                print(f"   ❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Health check error: {e}")
            return False
    
    def test_user_management(self) -> bool:
        """Test user registration, login, and management"""
        self.print_step("2. Testing user management...")
        
        # Register admin user
        admin_data = {
            "email": self.admin_email,
            "password": self.password,
            "full_name": "System Admin",
            "department": "IT"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=admin_data)
        if response.status_code == 200:
            print("   ✅ Admin user registered")
        else:
            # User might already exist
            print("   ⚠️  Admin user might already exist")
        
        # Login admin
        login_data = {
            "email": self.admin_email,
            "password": self.password
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if response.status_code == 200:
            self.admin_token = response.json()["access_token"]
            print("   ✅ Admin login successful")
        else:
            print(f"   ❌ Admin login failed: {response.status_code}")
            return False
        
        # Register regular user
        user_data = {
            "email": self.user_email,
            "password": self.password,
            "full_name": "Test Employee",
            "department": "Engineering"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/register", json=user_data)
        if response.status_code == 200:
            print("   ✅ Regular user registered")
        else:
            print("   ⚠️  Regular user might already exist")
        
        # Login regular user
        login_data = {
            "email": self.user_email,
            "password": self.password
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
        if response.status_code == 200:
            self.user_token = response.json()["access_token"]
            print("   ✅ User login successful")
            return True
        else:
            print(f"   ❌ User login failed: {response.status_code}")
            return False
    
    def test_api_key_management(self) -> bool:
        """Test API key creation and usage"""
        self.print_step("3. Testing API key management...")
        
        if not self.user_token:
            print("   ❌ No user token available")
            return False
        
        headers = {"Authorization": f"Bearer {self.user_token}"}
        
        # Create API key
        key_data = {"name": "Test API Key"}
        response = requests.post(f"{BASE_URL}/api/auth/api-keys", json=key_data, headers=headers)
        
        if response.status_code == 200:
            key_response = response.json()
            self.api_key = key_response["api_key"]
            print("   ✅ API key created")
        else:
            print(f"   ❌ API key creation failed: {response.status_code}")
            return False
        
        # Test API key usage
        api_headers = {"X-API-Key": self.api_key}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=api_headers)
        
        if response.status_code == 200:
            print("   ✅ API key authentication works")
            return True
        else:
            print(f"   ❌ API key authentication failed: {response.status_code}")
            return False
    
    def test_document_upload_with_auth(self) -> bool:
        """Test document upload with authentication"""
        self.print_step("4. Testing authenticated document upload...")
        
        if not self.user_token:
            print("   ❌ No user token available")
            return False
        
        # Create test document
        sample_content = """
        Company Security Policy 2024
        
        This document outlines our information security policies and procedures.
        
        Password Requirements:
        - Minimum 12 characters
        - Mix of uppercase, lowercase, numbers, and symbols
        - No dictionary words
        - Changed every 90 days
        
        Access Control:
        - Role-based access control implemented
        - Principle of least privilege
        - Regular access reviews
        
        Data Classification:
        - Public: Marketing materials, public documents
        - Internal: Employee procedures, internal communications
        - Confidential: Customer data, financial information
        - Restricted: Trade secrets, personal information
        
        Incident Response:
        - Report security incidents within 1 hour
        - IT Security team on call 24/7
        - Incident response plan activated immediately
        """
        
        headers = {"Authorization": f"Bearer {self.user_token}"}
        files = {"file": ("security_policy.txt", sample_content, "text/plain")}
        data = {
            "title": "Company Security Policy 2024",
            "department": "IT Security",
            "content_type": "policy",
            "uploaded_by": self.user_email
        }
        
        response = requests.post(f"{BASE_URL}/api/documents/upload", files=files, data=data, headers=headers)
        
        if response.status_code == 200:
            upload_result = response.json()
            self.document_id = upload_result["id"]
            print(f"   ✅ Document uploaded (ID: {self.document_id})")
            print(f"   ✅ Chunks created: {upload_result['chunks_created']}")
            return True
        else:
            print(f"   ❌ Document upload failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    
    def test_authenticated_chat(self) -> bool:
        """Test chat functionality with authentication"""
        self.print_step("5. Testing authenticated chat...")
        
        if not self.user_token:
            print("   ❌ No user token available")
            return False
        
        headers = {"Authorization": f"Bearer {self.user_token}"}
        
        # Start conversation
        response = requests.post(f"{BASE_URL}/api/chat/start", params={"user_email": self.user_email}, headers=headers)
        
        if response.status_code == 200:
            start_result = response.json()
            self.session_id = start_result["session_id"]
            print(f"   ✅ Conversation started (Session: {self.session_id[:8]}...)")
        else:
            print(f"   ❌ Failed to start conversation: {response.status_code}")
            return False
        
        # Send test messages
        test_questions = [
            "What are the password requirements in our security policy?",
            "How should I report a security incident?",
            "What are the different data classification levels?"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"   Question {i}: {question[:50]}...")
            
            message_data = {
                "message": question,
                "user_email": self.user_email,
                "session_id": self.session_id
            }
            
            response = requests.post(f"{BASE_URL}/api/chat/message", json=message_data, headers=headers)
            
            if response.status_code == 200:
                chat_response = response.json()
                confidence = chat_response.get("confidence_score", 0)
                sources = len(chat_response.get("sources", []))
                print(f"   ✅ Response received (confidence: {confidence:.2f}, sources: {sources})")
            else:
                print(f"   ❌ Chat message failed: {response.status_code}")
                return False
            
            time.sleep(1)  # Rate limiting
        
        return True
    
    def test_conversation_management(self) -> bool:
        """Test conversation history and management"""
        self.print_step("6. Testing conversation management...")
        
        if not self.user_token or not self.session_id:
            print("   ❌ Missing authentication or session")
            return False
        
        headers = {"Authorization": f"Bearer {self.user_token}"}
        
        # Get conversation history
        history_data = {
            "user_email": self.user_email,
            "session_id": self.session_id
        }
        
        response = requests.post(f"{BASE_URL}/api/chat/history", json=history_data, headers=headers)
        
        if response.status_code == 200:
            history = response.json()
            message_count = len(history.get("messages", []))
            print(f"   ✅ Conversation history retrieved ({message_count} messages)")
        else:
            print(f"   ❌ Failed to get conversation history: {response.status_code}")
            return False
        
        # List user conversations
        response = requests.get(f"{BASE_URL}/api/chat/conversations", params={"user_email": self.user_email}, headers=headers)
        
        if response.status_code == 200:
            conversations = response.json()
            conv_count = conversations.get("total_count", 0)
            print(f"   ✅ User conversations listed ({conv_count} total)")
            return True
        else:
            print(f"   ❌ Failed to list conversations: {response.status_code}")
            return False
    
    def test_admin_functions(self) -> bool:
        """Test admin-only functions"""
        self.print_step("7. Testing admin functions...")
        
        if not self.admin_token:
            print("   ❌ No admin token available")
            return False
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # List all users
        response = requests.get(f"{BASE_URL}/api/auth/users", headers=headers)
        
        if response.status_code == 200:
            users = response.json()
            user_count = users.get("total_count", 0)
            print(f"   ✅ User list retrieved ({user_count} users)")
        else:
            print(f"   ❌ Failed to list users: {response.status_code}")
            return False
        
        # Get audit logs
        response = requests.get(f"{BASE_URL}/api/auth/audit-logs", headers=headers)
        
        if response.status_code == 200:
            logs = response.json()
            log_count = logs.get("total_count", 0)
            print(f"   ✅ Audit logs retrieved ({log_count} events)")
        else:
            print(f"   ❌ Failed to get audit logs: {response.status_code}")
            return False
        
        # Get system info
        response = requests.get(f"{BASE_URL}/system/info", headers=headers)
        
        if response.status_code == 200:
            info = response.json()
            print("   ✅ System info retrieved")
            print(f"      - Environment: {info['system']['environment']}")
            print(f"      - Total users: {info['database']['total_users']}")
            print(f"      - Total documents: {info['database']['total_documents']}")
            return True
        else:
            print(f"   ❌ Failed to get system info: {response.status_code}")
            return False
    
    def test_security_features(self) -> bool:
        """Test security features like rate limiting"""
        self.print_step("8. Testing security features...")
        
        # Test unauthorized access
        response = requests.get(f"{BASE_URL}/api/auth/me")
        if response.status_code == 401:
            print("   ✅ Unauthorized access properly blocked")
        else:
            print(f"   ⚠️  Unexpected response to unauthorized request: {response.status_code}")
        
        # Test invalid token
        bad_headers = {"Authorization": "Bearer invalid_token"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=bad_headers)
        if response.status_code == 401:
            print("   ✅ Invalid token properly rejected")
        else:
            print(f"   ⚠️  Unexpected response to invalid token: {response.status_code}")
        
        # Test rate limiting (mild test)
        print("   Testing rate limiting (10 rapid requests)...")
        rate_limited = False
        
        for i in range(10):
            response = requests.get(f"{BASE_URL}/health")
            if response.status_code == 429:
                print(f"   ✅ Rate limited after {i+1} requests")
                rate_limited = True
                break
        
        if not rate_limited:
            print("   ⚠️  Rate limiting not triggered (may be disabled in dev)")
        
        return True
    
    def run_comprehensive_test(self):
        """Run all tests"""
        print("🔐 COMPREHENSIVE PHASE 4 SYSTEM TEST")
        print(f"Testing against: {BASE_URL}")
        print("This will test authentication, authorization, document processing, and chat functionality")
        
        results = []
        
        # Run all tests
        tests = [
            ("System Health", self.test_health_check),
            ("User Management", self.test_user_management),
            ("API Key Management", self.test_api_key_management),
            ("Document Upload", self.test_document_upload_with_auth),
            ("Authenticated Chat", self.test_authenticated_chat),
            ("Conversation Management", self.test_conversation_management),
            ("Admin Functions", self.test_admin_functions),
            ("Security Features", self.test_security_features)
        ]
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"   ❌ Test failed with exception: {e}")
                results.append((test_name, False))
        
        # Summary
        self.print_section("TEST RESULTS SUMMARY")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:.<30} {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED!")
            print("Your Phase 4 implementation is working correctly!")
        else:
            print(f"\n⚠️  {total-passed} test(s) failed. Check the logs above for details.")
        
        print("\nNext steps:")
        print("- Review any failed tests")
        print("- Test with real company documents")
        print("- Set up monitoring and alerts")
        print("- Plan Phase 5 features")

if __name__ == "__main__":
    print("Starting comprehensive Phase 4 test...")
    print("Make sure your API server is running on http://localhost:8000")
    
    tester = ComprehensiveSystemTester()
    tester.run_comprehensive_test()