import requests
import json

BASE_URL = "http://localhost:8000"

def safe_print_json(response):
    """Try to print response as JSON, fallback to raw text"""
    try:
        print(json.dumps(response.json(), indent=2))
    except Exception:
        print("Raw Response:", response.text)


def test_document_upload():
    """Test document upload with a simple text file"""
    
    # Create a sample document
    sample_content = """
    Company Remote Work Policy
    
    Employees are allowed to work remotely up to 3 days per week.
    Manager approval is required for remote work arrangements.
    All remote workers must maintain secure home office setups.
    
    Benefits of Remote Work:
    - Improved work-life balance
    - Reduced commuting time
    - Increased productivity
    - Lower office overhead costs
    
    Requirements:
    - Reliable internet connection
    - Secure workspace
    - Regular check-ins with team
    """
    
    # Prepare the upload
    files = {"file": ("remote_work_policy.txt", sample_content, "text/plain")}
    data = {
        "title": "Remote Work Policy 2024",
        "department": "HR", 
        "content_type": "policy",
        "uploaded_by": "admin@company.com"
    }
    
    response = requests.post(f"{BASE_URL}/api/documents/upload", files=files, data=data)
    print(f"Upload Status: {response.status_code}")
    safe_print_json(response)
    return response


def test_document_search():
    """Test semantic search"""
    
    search_data = {
        "query": "work from home requirements",
        "limit": 5
    }
    
    response = requests.post(f"{BASE_URL}/api/documents/search", json=search_data)
    print(f"Search Status: {response.status_code}")
    safe_print_json(response)


def test_list_documents():
    """Test listing documents"""
    
    response = requests.get(f"{BASE_URL}/api/documents/")
    print(f"List Status: {response.status_code}")
    safe_print_json(response)


if __name__ == "__main__":
    print("Testing Document API...")
    
    # Test upload
    test_document_upload()
    
    print("\n" + "="*50 + "\n")
    
    # Test search
    test_document_search()
    
    print("\n" + "="*50 + "\n")
    
    # Test list
    test_list_documents()
