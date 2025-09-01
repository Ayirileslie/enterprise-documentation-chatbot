import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

class ChatSystemTester:
    def __init__(self):
        self.session_id = None
        self.user_email = "test@company.com"
    
    def test_complete_workflow(self):
        """Test the complete workflow: upload document → chat about it"""
        
        print("🎯 Starting Complete Chat System Test")
        print("=" * 60)
        
        # Step 1: Upload a test document
        print("\n1. Uploading test document...")
        upload_result = self.upload_test_document()
        
        if upload_result.get("status_code") != 200:
            print(f"❌ Document upload failed: {upload_result}")
            return
        
        print(f"✅ Document uploaded successfully: {upload_result['data']['title']}")
        time.sleep(2)  # Allow processing time
        
        # Step 2: Start a new conversation
        print("\n2. Starting new conversation...")
        chat_start_result = self.start_conversation()
        
        if chat_start_result.get("status_code") != 200:
            print(f"❌ Failed to start conversation: {chat_start_result}")
            return
        
        self.session_id = chat_start_result["data"]["session_id"]
        print(f"✅ Conversation started with session ID: {self.session_id}")
        
        # Step 3: Test chat functionality
        print("\n3. Testing chat responses...")
        self.test_chat_interactions()
        
        # Step 4: Test conversation management
        print("\n4. Testing conversation management...")
        self.test_conversation_management()
        
        # Step 5: Test analytics
        print("\n5. Testing analytics...")
        self.test_analytics()
        
        print("\n🎉 Complete workflow test finished!")
    
    def upload_test_document(self) -> Dict[str, Any]:
        """Upload a sample document for testing"""
        
        sample_content = """
        Remote Work Policy - Updated 2024
        
        Overview:
        Our company supports flexible work arrangements to promote work-life balance
        and employee satisfaction. This policy outlines the guidelines for remote work.
        
        Eligibility:
        - Full-time employees with at least 6 months tenure
        - Employees with satisfactory performance reviews
        - Roles that can be performed effectively remotely
        
        Remote Work Guidelines:
        1. Maximum 3 days per week remote work
        2. Core hours: 10 AM - 3 PM in company timezone
        3. Manager approval required for remote work schedule
        4. Regular check-ins with team members
        
        Technology Requirements:
        - Reliable high-speed internet connection (minimum 25 Mbps)
        - Secure home office setup
        - Company-approved VPN access
        - Updated antivirus software
        
        Communication Expectations:
        - Respond to messages within 4 hours during business hours
        - Attend all scheduled meetings via video conference
        - Update project status daily in team channels
        - Maintain professional background for video calls
        
        Performance Monitoring:
        - Goals and deliverables remain unchanged
        - Weekly one-on-one meetings with manager
        - Monthly productivity assessments
        - Quarterly review of remote work arrangement
        
        Security Requirements:
        - Use company-issued devices only
        - Lock screen when away from workspace
        - No work in public spaces with sensitive information
        - Report security incidents immediately
        """
        
        try:
            files = {"file": ("remote_work_policy_2024.txt", sample_content, "text/plain")}
            data = {
                "title": "Remote Work Policy 2024",
                "department": "Human Resources",
                "content_type": "policy",
                "uploaded_by": "hr@company.com"
            }
            
            response = requests.post(f"{BASE_URL}/api/documents/upload", files=files, data=data)
            
            return {
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else None,
                "error": response.text if response.status_code != 200 else None
            }
            
        except Exception as e:
            return {"status_code": 500, "error": str(e)}
    
    def start_conversation(self) -> Dict[str, Any]:
        """Start a new conversation"""
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/chat/start",
                params={"user_email": self.user_email}
            )
            
            return {
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else None,
                "error": response.text if response.status_code != 200 else None
            }
            
        except Exception as e:
            return {"status_code": 500, "error": str(e)}
    
    def send_chat_message(self, message: str) -> Dict[str, Any]:
        """Send a message to the chatbot"""
        
        try:
            payload = {
                "message": message,
                "user_email": self.user_email,
                "session_id": self.session_id
            }
            
            response = requests.post(f"{BASE_URL}/api/chat/message", json=payload)
            
            return {
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else None,
                "error": response.text if response.status_code != 200 else None
            }
            
        except Exception as e:
            return {"status_code": 500, "error": str(e)}
    
    def test_chat_interactions(self):
        """Test various chat interactions"""
        
        test_questions = [
            "What is the company's remote work policy?",
            "How many days per week can I work from home?",
            "What are the technology requirements for remote work?",
            "What are the core hours for remote workers?",
            "Can you tell me about performance monitoring for remote employees?"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n   Question {i}: {question}")
            
            result = self.send_chat_message(question)
            
            if result["status_code"] == 200:
                response_data = result["data"]
                print(f"   ✅ Response received (confidence: {response_data.get('confidence_score', 'N/A')})")
                print(f"   📄 Sources used: {len(response_data.get('sources', []))}")
                
                # Show first 150 chars of response
                response_text = response_data.get("response", "")
                preview = response_text[:150] + "..." if len(response_text) > 150 else response_text
                print(f"   💬 Response preview: {preview}")
                
            else:
                print(f"   ❌ Failed: {result['error']}")
            
            time.sleep(1)  # Rate limiting
    
    def test_conversation_management(self):
        """Test conversation history and management"""
        
        # Get conversation history
        print("\n   Testing conversation history...")
        try:
            payload = {
                "user_email": self.user_email,
                "session_id": self.session_id
            }
            
            response = requests.post(f"{BASE_URL}/api/chat/history", json=payload)
            
            if response.status_code == 200:
                history = response.json()
                message_count = len(history.get("messages", []))
                print(f"   ✅ Retrieved conversation with {message_count} messages")
            else:
                print(f"   ❌ Failed to get history: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error getting history: {str(e)}")
        
        # Get user conversations
        print("\n   Testing user conversations list...")
        try:
            response = requests.get(
                f"{BASE_URL}/api/chat/conversations",
                params={"user_email": self.user_email}
            )
            
            if response.status_code == 200:
                conversations = response.json()
                conv_count = conversations.get("total_count", 0)
                print(f"   ✅ User has {conv_count} conversations")
            else:
                print(f"   ❌ Failed to get conversations: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error getting conversations: {str(e)}")
    
    def test_analytics(self):
        """Test analytics endpoint"""
        
        try:
            response = requests.get(f"{BASE_URL}/api/chat/analytics")
            
            if response.status_code == 200:
                analytics = response.json()
                print(f"   ✅ Analytics retrieved:")
                print(f"      - Total conversations: {analytics.get('total_conversations', 0)}")
                print(f"      - Total messages: {analytics.get('total_messages', 0)}")
                print(f"      - Average confidence: {analytics.get('average_confidence_score', 'N/A')}")
            else:
                print(f"   ❌ Failed to get analytics: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error getting analytics: {str(e)}")

def test_individual_endpoints():
    """Test individual endpoints without full workflow"""
    
    print("\n🔧 Testing Individual Endpoints")
    print("=" * 40)
    
    # Test health check
    print("\n1. Health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            health = response.json()
            print(f"   ✅ API is healthy")
            print(f"      - Database: {health.get('database', 'unknown')}")
            print(f"      - Vector store: {health.get('vector_store', 'unknown')}")
            print(f"      - LLM: {health.get('llm', 'unknown')}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Health check error: {str(e)}")
    
    # Test document endpoints
    print("\n2. Document endpoints...")
    try:
        response = requests.get(f"{BASE_URL}/api/documents/")
        print(f"   Documents list: {response.status_code}")
        
        response = requests.get(f"{BASE_URL}/api/documents/stats/overview")
        if response.status_code == 200:
            stats = response.json()
            print(f"   ✅ Document stats: {stats.get('total_documents', 0)} documents")
        
    except Exception as e:
        print(f"   ❌ Document endpoints error: {str(e)}")

if __name__ == "__main__":
    print("Starting Chat System Tests...")
    print("Make sure your API server is running on http://localhost:8000")
    
    # Test individual endpoints first
    test_individual_endpoints()
    
    # Run complete workflow test
    tester = ChatSystemTester()
    tester.test_complete_workflow()
    
    print("\n" + "=" * 60)
    print("Test Results Summary:")
    print("- Check for ✅ (success) and ❌ (failure) indicators above")
    print("- Review any error messages")
    print("- Verify your .env file has OPENAI_API_KEY set")
    print("- Make sure all dependencies are installed")
    print("=" * 60)