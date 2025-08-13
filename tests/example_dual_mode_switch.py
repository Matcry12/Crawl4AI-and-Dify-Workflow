#!/usr/bin/env python3
"""
Example showing how to switch between word-based and token-based thresholds
"""

import asyncio
import os
from dotenv import load_dotenv
from crawl_workflow import CrawlWorkflow

async def test_with_word_threshold():
    """Example using word count threshold (default)"""
    print("=" * 60)
    print("🔤 TEST 1: Using WORD COUNT threshold")
    print("=" * 60)
    
    workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key=os.getenv('DIFY_API_KEY', 'your-api-key'),
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        enable_dual_mode=True,
        word_threshold=4000,      # 4000 words threshold
        use_word_threshold=True   # Use word count (default)
    )
    
    # Test with a URL
    await workflow.crawl_and_process(
        url="https://example.com/docs",
        max_pages=1,
        max_depth=0,
        extraction_model="gemini/gemini-2.0-flash-exp"
    )

async def test_with_token_threshold():
    """Example using token count threshold"""
    print("\n" + "=" * 60)
    print("🎯 TEST 2: Using TOKEN COUNT threshold")
    print("=" * 60)
    
    workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key=os.getenv('DIFY_API_KEY', 'your-api-key'),
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        enable_dual_mode=True,
        token_threshold=8000,      # 8000 tokens threshold
        use_word_threshold=False   # Use token count instead
    )
    
    # Test with the same URL
    await workflow.crawl_and_process(
        url="https://example.com/docs",
        max_pages=1,
        max_depth=0,
        extraction_model="gemini/gemini-2.0-flash-exp"
    )

async def test_custom_thresholds():
    """Example with custom thresholds"""
    print("\n" + "=" * 60)
    print("⚙️  TEST 3: Custom thresholds")
    print("=" * 60)
    
    # Example 1: Very low word threshold for testing
    workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key=os.getenv('DIFY_API_KEY', 'your-api-key'),
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        enable_dual_mode=True,
        word_threshold=1000,       # Only 1000 words threshold
        use_word_threshold=True
    )
    
    print("Testing with 1000 word threshold...")
    # Most content will be in paragraph mode with this low threshold

async def main():
    """Run all examples"""
    load_dotenv(override=True)
    
    print("🚀 Dual-Mode Threshold Switching Examples")
    print("This demonstrates how to switch between word and token thresholds")
    print()
    
    # Test 1: Word threshold
    await test_with_word_threshold()
    
    # Test 2: Token threshold  
    await test_with_token_threshold()
    
    # Test 3: Custom thresholds
    await test_custom_thresholds()
    
    print("\n✅ All tests completed!")
    print("\n📌 Quick Reference:")
    print("  • use_word_threshold=True  → Uses word count (default)")
    print("  • use_word_threshold=False → Uses token count")
    print("  • word_threshold=4000      → Default 4000 words")
    print("  • token_threshold=8000     → Default 8000 tokens")

if __name__ == "__main__":
    asyncio.run(main())