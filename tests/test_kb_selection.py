#!/usr/bin/env python3
"""
Test script for knowledge base selection feature
"""

import asyncio
import os
from dotenv import load_dotenv
from crawl_workflow import CrawlWorkflow

async def test_automatic_mode():
    """Test automatic knowledge base selection"""
    print("=" * 80)
    print("TEST 1: Automatic Knowledge Base Selection")
    print("=" * 80)
    
    workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key="dataset-VoYPMEaQ8L1udk2F6oek99XK",
        knowledge_base_mode='automatic'  # Automatic mode
    )
    
    await workflow.initialize()
    
    # Test categorization with different content
    test_cases = [
        ("https://docs.eosnetwork.com/", "EOS blockchain documentation content"),
        ("https://bitcoin.org/", "Bitcoin cryptocurrency content"),
        ("https://react.dev/", "React JavaScript framework content")
    ]
    
    for url, content in test_cases:
        print(f"\nTesting URL: {url}")
        category, tags = await workflow.categorize_content(content, url)
        print(f"  Category: {category}")
        print(f"  Tags: {tags}")

async def test_manual_mode():
    """Test manual knowledge base selection"""
    print("\n" + "=" * 80)
    print("TEST 2: Manual Knowledge Base Selection")
    print("=" * 80)
    
    workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key="dataset-VoYPMEaQ8L1udk2F6oek99XK",
        knowledge_base_mode='automatic'  # Start with automatic to get KB list
    )
    
    await workflow.initialize()
    
    # Get existing knowledge bases
    print("\nExisting Knowledge Bases:")
    for name, kb_id in workflow.knowledge_bases.items():
        print(f"  - {name} (ID: {kb_id})")
    
    if workflow.knowledge_bases:
        # Pick the first KB for testing
        first_kb_name = list(workflow.knowledge_bases.keys())[0]
        first_kb_id = workflow.knowledge_bases[first_kb_name]
        
        print(f"\nUsing manual mode with KB: {first_kb_name} (ID: {first_kb_id})")
        
        # Create a new workflow instance with manual mode
        manual_workflow = CrawlWorkflow(
            dify_base_url="http://localhost:8088",
            dify_api_key="dataset-VoYPMEaQ8L1udk2F6oek99XK",
            knowledge_base_mode='manual',
            selected_knowledge_base=first_kb_id
        )
        
        await manual_workflow.initialize()
        
        # Test processing content with manual KB
        test_content = {
            'title': 'Test Document',
            'description': 'This is a test document for manual KB selection'
        }
        
        success, status = await manual_workflow.process_crawled_content(
            test_content, 
            "https://example.com/test"
        )
        
        print(f"\nProcessing result: {success} (status: {status})")

async def main():
    """Run all tests"""
    load_dotenv(override=True)
    
    await test_automatic_mode()
    await test_manual_mode()
    
    print("\n" + "=" * 80)
    print("TESTS COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())