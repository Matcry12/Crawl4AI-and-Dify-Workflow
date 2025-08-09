#!/usr/bin/env python3
"""
Simple test to verify Dify document creation and visibility
"""

import requests
import json
import time

def test_simple_push():
    """Test the simplest possible document push to Dify."""
    
    # Configuration
    base_url = "http://localhost:8088"
    api_key = "dataset-VoYPMEaQ8L1udk2F6oek99XK"
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    print("🔍 SIMPLE DIFY PUSH TEST")
    print("=" * 80)
    
    # Step 1: Get first knowledge base
    print("\n1️⃣ Getting knowledge bases...")
    url = f"{base_url}/v1/datasets"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Failed to get knowledge bases: {response.status_code}")
        print(response.text)
        return
    
    kb_data = response.json()
    print(f"Response structure: {list(kb_data.keys())}")
    
    # Find first KB
    kb_id = None
    kb_name = None
    
    if 'data' in kb_data and kb_data['data']:
        kb = kb_data['data'][0]
        kb_id = kb.get('id')
        kb_name = kb.get('name')
        print(f"✅ Found KB: {kb_name} (ID: {kb_id})")
    else:
        print("❌ No knowledge bases found")
        return
    
    # Step 2: Create a very simple document
    print(f"\n2️⃣ Creating simple document in KB: {kb_id}")
    
    # Try the absolute simplest structure first
    doc_data = {
        "name": f"test_doc_{int(time.time())}",
        "text": "This is a simple test document. It contains basic text without any special formatting or separators.",
        "indexing_technique": "high_quality"
    }
    
    url = f"{base_url}/v1/datasets/{kb_id}/document/create-by-text"
    print(f"POST to: {url}")
    print(f"Data: {json.dumps(doc_data, indent=2)}")
    
    response = requests.post(url, headers=headers, json=doc_data)
    print(f"\nResponse status: {response.status_code}")
    
    try:
        response_data = response.json()
        print(f"Response: {json.dumps(response_data, indent=2)}")
        
        # Check if document ID was returned
        doc_id = None
        if 'document' in response_data:
            doc_id = response_data['document'].get('id')
        elif 'id' in response_data:
            doc_id = response_data['id']
        
        if doc_id:
            print(f"✅ Document created with ID: {doc_id}")
        else:
            print("⚠️  No document ID in response")
            
    except Exception as e:
        print(f"❌ Failed to parse response: {e}")
        print(f"Raw response: {response.text}")
    
    # Step 3: Wait and check document list
    print("\n3️⃣ Waiting 5 seconds for processing...")
    time.sleep(5)
    
    print(f"\n4️⃣ Checking documents in KB: {kb_id}")
    url = f"{base_url}/v1/datasets/{kb_id}/documents"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        docs_data = response.json()
        doc_list = docs_data.get('data', [])
        
        print(f"\n📊 Found {len(doc_list)} documents:")
        for doc in doc_list[:5]:  # Show first 5
            print(f"  - Name: {doc.get('name')}")
            print(f"    ID: {doc.get('id')}")
            print(f"    Status: {doc.get('indexing_status', 'unknown')}")
            print(f"    Created: {doc.get('created_at', 'unknown')}")
            print()
            
        # Look for our test document
        test_docs = [d for d in doc_list if d.get('name', '').startswith('test_doc_')]
        if test_docs:
            print(f"✅ Found {len(test_docs)} test documents")
        else:
            print("⚠️  No test documents found")
            
    else:
        print(f"❌ Failed to get documents: {response.status_code}")
        print(response.text)
    
    # Step 5: Try with automatic mode
    print("\n5️⃣ Testing with automatic segmentation mode...")
    doc_data_auto = {
        "name": f"test_auto_doc_{int(time.time())}",
        "text": "This is a test with automatic segmentation. The content should be processed automatically by Dify.",
        "indexing_technique": "high_quality",
        "process_rule": {
            "mode": "automatic"
        }
    }
    
    response = requests.post(f"{base_url}/v1/datasets/{kb_id}/document/create-by-text", 
                           headers=headers, json=doc_data_auto)
    print(f"Auto mode response status: {response.status_code}")
    
    # Step 6: Check document indexing status
    print("\n6️⃣ Tips for troubleshooting:")
    print("- Documents may show status 'indexing' for a while")
    print("- Check the Dify web UI to see if documents appear there")
    print("- Look for any error messages in Dify logs")
    print("- Ensure your API key has write permissions")
    print("- Try creating a document through Dify UI to compare")

if __name__ == "__main__":
    test_simple_push()