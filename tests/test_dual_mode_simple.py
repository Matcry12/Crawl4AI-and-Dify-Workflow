#!/usr/bin/env python3
"""
Simple test script to verify dual-mode functionality
"""

import asyncio
import os
from dotenv import load_dotenv
from crawl_workflow import CrawlWorkflow

async def test_dual_mode():
    """Test the dual-mode functionality with a real URL."""
    load_dotenv(override=True)
    
    # Test URLs - one likely short, one likely long
    test_urls = [
        "https://docs.python.org/3/library/json.html",  # Likely short - API reference
        "https://docs.python.org/3/tutorial/index.html"  # Likely long - full tutorial
    ]
    
    print("🚀 Testing Dual-Mode RAG Knowledge Base")
    print("=" * 80)
    
    # Initialize workflow with dual-mode enabled
    workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key=os.getenv('DIFY_API_KEY', 'dataset-VoYPMEaQ8L1udk2F6oek99XK'),
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        enable_dual_mode=True,
        token_threshold=8000,
        naming_model="gemini/gemini-1.5-flash"
    )
    
    print("\n📊 Configuration:")
    print(f"  • Dual-mode: ENABLED")
    print(f"  • Token threshold: 8000 tokens")
    print(f"  • Mode selection: Automatic based on content length")
    print("\n" + "=" * 80)
    
    # Test each URL
    for url in test_urls:
        print(f"\n🔍 Testing URL: {url}")
        print("-" * 60)
        
        try:
            await workflow.crawl_and_process(
                url=url,
                max_pages=1,
                max_depth=0,
                extraction_model="gemini/gemini-2.0-flash-exp"
            )
            print(f"✅ Successfully processed: {url}")
        except Exception as e:
            print(f"❌ Error processing {url}: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 80)
    
    print("\n✅ Test completed!")
    print("\nCheck the logs above to see:")
    print("1. Token count analysis for each URL")
    print("2. Selected processing mode (paragraph vs full_doc)")
    print("3. Section/chunk structure in the output")

if __name__ == "__main__":
    asyncio.run(test_dual_mode())