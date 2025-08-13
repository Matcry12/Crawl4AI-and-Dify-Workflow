#!/usr/bin/env python3
"""
Test script to demonstrate dual-mode RAG knowledge base functionality.
This script tests the automatic selection between paragraph mode and full doc mode.
"""

import asyncio
import os
from dotenv import load_dotenv
from crawl_workflow import CrawlWorkflow

async def test_dual_mode():
    """Test the dual-mode functionality with various content types."""
    load_dotenv(override=True)
    
    # Test URLs with different content lengths
    test_urls = [
        {
            "url": "https://example.com/api/quickstart",  # Likely short content -> full doc mode
            "description": "API quickstart guide (expected: full doc mode)"
        },
        {
            "url": "https://example.com/docs/comprehensive-guide",  # Likely long content -> paragraph mode
            "description": "Comprehensive documentation (expected: paragraph mode)"
        },
        {
            "url": "https://example.com/faq",  # FAQ page -> full doc mode (URL pattern)
            "description": "FAQ page (expected: full doc mode due to URL pattern)"
        }
    ]
    
    # Initialize workflow with dual-mode enabled
    print("🚀 Initializing Crawl4AI with Dual-Mode Support")
    print("=" * 80)
    
    workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key=os.getenv('DIFY_API_KEY', 'your-api-key-here'),
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        enable_dual_mode=True,
        token_threshold=8000,  # Content under 8000 tokens uses full doc mode
        naming_model="gemini/gemini-1.5-flash"
    )
    
    print("\n📊 Configuration:")
    print(f"  • Dual-mode: ENABLED")
    print(f"  • Token threshold: 8000 tokens")
    print(f"  • Below threshold: Full document mode (no chunking)")
    print(f"  • Above threshold: Paragraph mode (parent-child chunks)")
    print(f"  • Special URLs (API, FAQ, etc.): Full document mode")
    print("\n" + "=" * 80)
    
    # Process each test URL
    for test_case in test_urls:
        print(f"\n🔍 Testing: {test_case['description']}")
        print(f"   URL: {test_case['url']}")
        print("-" * 60)
        
        await workflow.crawl_and_process(
            url=test_case['url'],
            max_pages=1,  # Only process the single URL
            max_depth=0,  # No deep crawling
            extraction_model="gemini/gemini-2.0-flash-exp"
        )
        
        print("\n" + "=" * 80)

async def test_threshold_variations():
    """Test different token thresholds to see mode selection behavior."""
    load_dotenv(override=True)
    
    test_thresholds = [4000, 8000, 12000]
    test_url = "https://docs.example.com/getting-started"
    
    print("🧪 Testing Different Token Thresholds")
    print("=" * 80)
    
    for threshold in test_thresholds:
        print(f"\n📏 Testing with threshold: {threshold} tokens")
        print("-" * 60)
        
        workflow = CrawlWorkflow(
            dify_base_url="http://localhost:8088",
            dify_api_key=os.getenv('DIFY_API_KEY', 'your-api-key-here'),
            gemini_api_key=os.getenv('GEMINI_API_KEY'),
            enable_dual_mode=True,
            token_threshold=threshold,
            naming_model="gemini/gemini-1.5-flash"
        )
        
        await workflow.crawl_and_process(
            url=test_url,
            max_pages=1,
            max_depth=0,
            extraction_model="gemini/gemini-2.0-flash-exp"
        )

async def test_manual_vs_automatic():
    """Compare manual mode selection vs automatic dual-mode."""
    load_dotenv(override=True)
    
    test_url = "https://docs.example.com/tutorial"
    
    print("🔄 Comparing Manual vs Automatic Mode Selection")
    print("=" * 80)
    
    # Test 1: Manual paragraph mode (legacy)
    print("\n1️⃣ Manual Paragraph Mode (Legacy)")
    print("-" * 60)
    
    workflow_manual = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key=os.getenv('DIFY_API_KEY', 'your-api-key-here'),
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        enable_dual_mode=False,  # Disable dual mode
        use_parent_child=True,   # Force paragraph mode
        naming_model="gemini/gemini-1.5-flash"
    )
    
    await workflow_manual.crawl_and_process(
        url=test_url,
        max_pages=1,
        max_depth=0,
        extraction_model="gemini/gemini-2.0-flash-exp"
    )
    
    # Test 2: Automatic dual-mode
    print("\n2️⃣ Automatic Dual-Mode")
    print("-" * 60)
    
    workflow_auto = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key=os.getenv('DIFY_API_KEY', 'your-api-key-here'),
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        enable_dual_mode=True,   # Enable dual mode
        token_threshold=8000,
        naming_model="gemini/gemini-1.5-flash"
    )
    
    await workflow_auto.crawl_and_process(
        url=test_url,
        max_pages=1,
        max_depth=0,
        extraction_model="gemini/gemini-2.0-flash-exp"
    )

async def main():
    """Run all tests."""
    print("🚀 Crawl4AI Dual-Mode Testing Suite")
    print("=" * 80)
    print("\nThis test suite demonstrates the automatic selection between:")
    print("• Paragraph mode (parent-child chunks) for long content")
    print("• Full document mode (no chunking) for short content")
    print("\n" + "=" * 80)
    
    # Run basic dual-mode test
    await test_dual_mode()
    
    # Uncomment to run additional tests:
    # await test_threshold_variations()
    # await test_manual_vs_automatic()
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())