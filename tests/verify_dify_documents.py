#!/usr/bin/env python3
"""
Verify document visibility in Dify after creation
"""

import asyncio
import json
import time
from Test_dify import DifyAPI
from crawl_workflow import CrawlWorkflow
import os
from dotenv import load_dotenv

async def verify_document_visibility():
    """Create a document and track its visibility over time."""
    
    load_dotenv(override=True)
    
    # Initialize workflow
    workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key="dataset-VoYPMEaQ8L1udk2F6oek99XK",
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        use_parent_child=True
    )
    
    # Initialize to get knowledge bases
    await workflow.initialize()
    
    if not workflow.knowledge_bases:
        print("❌ No knowledge bases found")
        return
    
    # Get first knowledge base
    kb_name, kb_id = list(workflow.knowledge_bases.items())[0]
    print(f"Using knowledge base: {kb_name} (ID: {kb_id})")
    
    # Create test content
    test_content = {
        'title': 'Visibility Test Document',
        'description': """###PARENT_SECTION###[Test Overview]
This is a test document to verify visibility in Dify.

###CHILD_SECTION###[Test Details]
This section contains test details to ensure proper chunking.

###CHILD_SECTION###[Additional Information]
More content to test the parent-child structure."""
    }
    
    # Create unique test URL
    test_url = f"https://test.example.com/visibility_test_{int(time.time())}"
    
    print(f"\n1️⃣ Creating document from URL: {test_url}")
    success, status = await workflow.push_to_knowledge_base(kb_id, test_content, test_url)
    
    if not success:
        print("❌ Failed to create document")
        return
    
    print(f"\n2️⃣ Document creation status: {status}")
    
    # Check visibility immediately and after delays
    check_intervals = [0, 5, 10, 20, 30]
    
    for interval in check_intervals:
        if interval > 0:
            print(f"\n⏳ Waiting {interval} seconds...")
            await asyncio.sleep(interval)
        
        print(f"\n3️⃣ Checking documents (after {interval}s):")
        
        # Force reload documents
        workflow.document_cache.pop(kb_id, None)
        docs = await workflow.load_documents_for_knowledge_base(kb_id)
        
        print(f"Total documents found: {len(docs)}")
        
        # Look for our test document
        doc_name = workflow.generate_document_name(test_url)
        if doc_name in docs:
            print(f"✅ Test document FOUND: {doc_name} (ID: {docs[doc_name]})")
            
            # Get detailed document info
            try:
                response = workflow.dify_api.get_document_list(kb_id, page=1, limit=100)
                if response.status_code == 200:
                    doc_list = response.json().get('data', [])
                    for doc in doc_list:
                        if doc.get('name') == doc_name:
                            print(f"\nDocument details:")
                            print(f"  - Name: {doc.get('name')}")
                            print(f"  - ID: {doc.get('id')}")
                            print(f"  - Status: {doc.get('indexing_status', 'unknown')}")
                            print(f"  - Created: {doc.get('created_at', 'unknown')}")
                            print(f"  - Word count: {doc.get('word_count', 'unknown')}")
                            print(f"  - Segment count: {doc.get('segment_count', 'unknown')}")
                            break
            except Exception as e:
                print(f"Error getting document details: {e}")
            
            break
        else:
            print(f"⏳ Test document NOT YET visible: {doc_name}")
            
            # Show some existing documents for comparison
            if docs and interval == 0:
                print("\nSome existing documents:")
                for i, (name, doc_id) in enumerate(list(docs.items())[:3]):
                    print(f"  - {name} (ID: {doc_id})")
    
    # Final check with direct API call
    print("\n4️⃣ Direct API check for all documents:")
    response = workflow.dify_api.get_document_list(kb_id, page=1, limit=10)
    if response.status_code == 200:
        doc_data = response.json()
        print(f"API Response structure: {list(doc_data.keys())}")
        doc_list = doc_data.get('data', [])
        print(f"Found {len(doc_list)} documents via direct API")
        
        # Show recent documents
        if doc_list:
            print("\nMost recent documents:")
            for doc in doc_list[:5]:
                print(f"  - {doc.get('name')} (Status: {doc.get('indexing_status', 'unknown')})")

if __name__ == "__main__":
    asyncio.run(verify_document_visibility())