# debug_endpoints.py
import requests
import json

API_BASE = "http://localhost:8000"

def test_endpoints():
    print("Testing API Endpoints...")
    print("=" * 50)
    
    # Test 1: Basic health check
    print("1. Testing Health Endpoint:")
    try:
        response = requests.get(f"{API_BASE}/health")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            health = response.json()
            print(f"   Response: {json.dumps(health, indent=2)}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Failed: {e}")
    
    print("\n" + "=" * 50)
    
    # Test 2: Root endpoint
    print("2. Testing Root Endpoint:")
    try:
        response = requests.get(f"{API_BASE}/")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Failed: {e}")
    
    print("\n" + "=" * 50)
    
    # Test 3: Documents endpoint
    print("3. Testing Documents List:")
    try:
        response = requests.get(f"{API_BASE}/api/documents/")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            docs = response.json()
            print(f"   Documents found: {len(docs)}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Failed: {e}")
    
    print("\n" + "=" * 50)
    
    # Test 4: Chat conversations (the failing one)
    print("4. Testing Chat Conversations:")
    test_email = "test@company.com"
    try:
        response = requests.get(f"{API_BASE}/api/chat/conversations?user_email={test_email}")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            convs = response.json()
            print(f"   Conversations: {json.dumps(convs, indent=2)}")
        else:
            print(f"   Error: {response.text}")
            print(f"   This is the failing endpoint!")
    except Exception as e:
        print(f"   Failed: {e}")
    
    print("\n" + "=" * 50)
    
    # Test 5: Start conversation
    print("5. Testing Start Conversation:")
    try:
        response = requests.post(f"{API_BASE}/api/chat/start?user_email={test_email}")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Session created: {result.get('session_id', 'No session ID')}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Failed: {e}")

if __name__ == "__main__":
    test_endpoints()