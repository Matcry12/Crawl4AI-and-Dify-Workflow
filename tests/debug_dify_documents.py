#!/usr/bin/env python3
"""
Debug script to check document creation and visibility in Dify
"""

import json
from Test_dify import DifyAPI
import time

def debug_document_creation():
    """Test document creation and check various API responses."""
    
    # Initialize API
    api = DifyAPI(
        base_url="http://localhost:8088",
        api_key="dataset-VoYPMEaQ8L1udk2F6oek99XK"  # Replace with your API key
    )
    
    print("🔍 DIFY DOCUMENT CREATION DEBUG")
    print("=" * 80)
    
    # Step 1: Get existing knowledge bases
    print("\n1️⃣ Fetching existing knowledge bases...")
    response = api.get_knowledge_base_list()
    if response.status_code == 200:
        kb_data = response.json()
        print(f"Response: {json.dumps(kb_data, indent=2)}")
        
        # Extract first knowledge base ID for testing
        kb_id = None
        if isinstance(kb_data, dict) and 'data' in kb_data:
            kb_list = kb_data['data']
            if kb_list and len(kb_list) > 0:
                kb_id = kb_list[0].get('id')
                kb_name = kb_list[0].get('name')
                print(f"\n✅ Using knowledge base: {kb_name} (ID: {kb_id})")
        
        if not kb_id:
            print("❌ No knowledge base found. Creating one...")
            # Create a test knowledge base
            create_response = api.create_empty_knowledge_base("Test Debug KB")
            if create_response.status_code == 200:
                create_data = create_response.json()
                print(f"Create response: {json.dumps(create_data, indent=2)}")
                kb_id = create_data.get('id')
            else:
                print(f"❌ Failed to create KB: {create_response.status_code} - {create_response.text}")
                return
    else:
        print(f"❌ Failed to get knowledge bases: {response.status_code} - {response.text}")
        return
    
    if not kb_id:
        print("❌ No knowledge base ID available")
        return
    
    # Step 2: Create test documents with different configurations
    print(f"\n2️⃣ Creating test documents in KB: {kb_id}")
    
    # Test 1: Simple flat document
    print("\n📄 Test 1: Simple flat document")
    flat_content = """This is a test document for debugging Dify.

###SECTION_BREAK###[Section 1: Introduction]
This is the introduction section with some content.

###SECTION_BREAK###[Section 2: Details]
This is the details section with more content."""
    
    response = api.create_document_from_text(
        dataset_id=kb_id,
        name="debug_flat_doc",
        text=flat_content,
        use_parent_child=False
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Wait a bit for processing
    time.sleep(2)
    
    # Test 2: Parent-child document
    print("\n📄 Test 2: Parent-child document")
    hierarchical_content = """###PARENT_SECTION###[Main Topic Overview]
This is the parent section providing an overview of the topic.

###CHILD_SECTION###[Specific Detail 1]
This is the first child section with specific details.

###CHILD_SECTION###[Specific Detail 2]
This is the second child section with more details.

###PARENT_SECTION###[Another Topic]
This is another parent section.

###CHILD_SECTION###[Sub-detail A]
Child content for the second parent."""
    
    response = api.create_document_from_text(
        dataset_id=kb_id,
        name="debug_hierarchical_doc",
        text=hierarchical_content,
        use_parent_child=True
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Wait for processing
    time.sleep(2)
    
    # Step 3: Check if documents are visible
    print(f"\n3️⃣ Checking documents in KB: {kb_id}")
    response = api.get_document_list(kb_id)
    
    if response.status_code == 200:
        doc_data = response.json()
        print(f"Document list response: {json.dumps(doc_data, indent=2)}")
        
        # Count and display documents
        doc_list = doc_data.get('data', [])
        print(f"\n📊 Found {len(doc_list)} documents:")
        for doc in doc_list:
            print(f"  - {doc.get('name')} (ID: {doc.get('id')})")
            print(f"    Status: {doc.get('status', 'unknown')}")
            print(f"    Created: {doc.get('created_at', 'unknown')}")
    else:
        print(f"❌ Failed to get documents: {response.status_code} - {response.text}")
    
    # Step 4: Test minimal document creation
    print("\n4️⃣ Testing minimal document creation")
    minimal_data = {
        "name": "minimal_test_doc",
        "text": "This is a minimal test document without any special formatting.",
        "indexing_technique": "high_quality"
    }
    
    response = api.dify_api.requests.post(
        f"{api.base_url}/v1/datasets/{kb_id}/document/create-by-text",
        headers=api.headers,
        json=minimal_data
    )
    
    print(f"Minimal doc response status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    print("\n✅ Debug complete!")
    print("\nPossible issues to check:")
    print("1. Document status might be 'indexing' - wait and refresh")
    print("2. Check Dify UI directly to see if documents appear there")
    print("3. Verify API key has correct permissions")
    print("4. Check Dify logs for any processing errors")

if __name__ == "__main__":
    debug_document_creation()