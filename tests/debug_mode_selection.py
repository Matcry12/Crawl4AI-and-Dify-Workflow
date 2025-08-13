#!/usr/bin/env python3
"""
Debug script to test mode selection and prompt generation
"""

import asyncio
import os
from dotenv import load_dotenv
from crawl_workflow import CrawlWorkflow

async def debug_mode_selection():
    """Debug the mode selection process."""
    load_dotenv(override=True)
    
    # Test URLs with different expected behaviors
    test_cases = [
        {
            "url": "https://httpbin.org/html",  # Simple HTML page - should be full_doc
            "expected_mode": "full_doc",
            "reason": "Short content"
        },
        {
            "url": "https://example.com/api/users",  # API pattern - should be full_doc
            "expected_mode": "full_doc", 
            "reason": "API URL pattern"
        }
    ]
    
    print("🔍 Debug Mode Selection")
    print("=" * 60)
    
    # Initialize workflow with dual-mode enabled
    workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key=os.getenv('DIFY_API_KEY', 'test-key'),
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        enable_dual_mode=True,
        token_threshold=8000,
        naming_model="gemini/gemini-1.5-flash"
    )
    
    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['url']}")
        print(f"Expected: {test_case['expected_mode']} ({test_case['reason']})")
        print("-" * 60)
        
        try:
            # Test just the mode selection process
            await workflow.crawl_and_process(
                url=test_case['url'],
                max_pages=1,
                max_depth=0,
                extraction_model="gemini/gemini-2.0-flash-exp"
            )
            
        except Exception as e:
            print(f"❌ Error: {e}")
            # Continue with next test case

if __name__ == "__main__":
    print("🚀 Starting Mode Selection Debug")
    asyncio.run(debug_mode_selection())