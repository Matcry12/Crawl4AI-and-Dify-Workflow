#!/usr/bin/env python3
"""
Example demonstrating the intelligent content analysis mode for RAG optimization.

This mode uses LLM to:
1. Assess content value (skip low-value pages)
2. Analyze content structure to determine optimal processing mode
3. Make intelligent decisions about how to chunk content
"""

import asyncio
import os
from dotenv import load_dotenv
from crawl_workflow import CrawlWorkflow

async def test_intelligent_mode():
    """Test the intelligent content analysis mode."""
    load_dotenv(override=True)
    
    print("🤖 Intelligent Mode RAG Optimization Demo")
    print("=" * 60)
    print("This mode uses LLM to analyze content and make smart decisions:")
    print("- Filter out low-value pages (navigation, login, etc.)")
    print("- Single topic content → Full doc mode (returns entire doc)")
    print("- Multi-topic content → Paragraph mode (returns specific chunks)")
    print("=" * 60)
    
    # Initialize workflow with intelligent mode
    workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key=os.getenv('DIFY_API_KEY', 'your-api-key'),
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        enable_dual_mode=True,
        use_intelligent_mode=True,  # Enable intelligent analysis
        intelligent_analysis_model="gemini/gemini-1.5-flash",  # Fast model for analysis
        naming_model="gemini/gemini-1.5-flash"  # Fast model for naming
    )
    
    # Test with various content types
    test_urls = [
        "https://example.com/tutorial/python-basics",  # Should be full_doc
        "https://example.com/blog",  # Should be paragraph (multi-topic)
        "https://example.com/api/users",  # Should be full_doc (API docs)
        "https://example.com/login",  # Should be skipped (low value)
    ]
    
    for url in test_urls:
        print(f"\n🔍 Testing: {url}")
        await workflow.crawl_and_process(
            url=url,
            max_pages=1,
            max_depth=0,
            extraction_model="gemini/gemini-2.0-flash-exp"
        )

async def compare_modes():
    """Compare intelligent mode vs threshold-based mode."""
    load_dotenv(override=True)
    
    print("\n📊 Comparing Mode Selection Approaches")
    print("=" * 60)
    
    test_url = "https://docs.example.com/guide"
    
    # Test 1: Threshold-based mode
    print("\n1️⃣ THRESHOLD-BASED MODE (4000 words)")
    print("-" * 60)
    
    workflow_threshold = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key=os.getenv('DIFY_API_KEY', 'your-api-key'),
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        enable_dual_mode=True,
        use_intelligent_mode=False,  # Use threshold
        word_threshold=4000
    )
    
    await workflow_threshold.crawl_and_process(
        url=test_url,
        max_pages=1,
        max_depth=0,
        extraction_model="gemini/gemini-2.0-flash-exp"
    )
    
    # Test 2: Intelligent mode
    print("\n2️⃣ INTELLIGENT MODE (LLM Analysis)")
    print("-" * 60)
    
    workflow_intelligent = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key=os.getenv('DIFY_API_KEY', 'your-api-key'),
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        enable_dual_mode=True,
        use_intelligent_mode=True,  # Use LLM
        intelligent_analysis_model="gemini/gemini-1.5-flash"
    )
    
    await workflow_intelligent.crawl_and_process(
        url=test_url,
        max_pages=1,
        max_depth=0,
        extraction_model="gemini/gemini-2.0-flash-exp"
    )

async def test_skip_low_value():
    """Demonstrate skipping low-value pages."""
    load_dotenv(override=True)
    
    print("\n⏭️  Testing Low-Value Page Filtering")
    print("=" * 60)
    print("Intelligent mode will skip pages like:")
    print("- Login/signup pages")
    print("- Navigation/index pages")
    print("- Cookie notices")
    print("- Error pages")
    print("=" * 60)
    
    workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key=os.getenv('DIFY_API_KEY', 'your-api-key'),
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        enable_dual_mode=True,
        use_intelligent_mode=True,
        intelligent_analysis_model="gemini/gemini-1.5-flash"
    )
    
    # URLs that should be skipped
    low_value_urls = [
        "https://example.com/login",
        "https://example.com/signup",
        "https://example.com/cookies-policy",
        "https://example.com/404",
        "https://example.com/sitemap"
    ]
    
    print("\nCrawling potentially low-value pages...")
    await workflow.crawl_and_process(
        url=low_value_urls[0],  # Start from one URL
        max_pages=10,
        max_depth=1,
        extraction_model="gemini/gemini-2.0-flash-exp"
    )

async def main():
    """Run all examples."""
    print("🚀 Intelligent Content Analysis Examples")
    print("This demonstrates the AI-powered content filtering and mode selection")
    print()
    
    # Example 1: Basic intelligent mode
    await test_intelligent_mode()
    
    # Example 2: Compare modes
    await compare_modes()
    
    # Example 3: Skip low-value pages
    await test_skip_low_value()
    
    print("\n✅ All examples completed!")
    print("\n📝 Key Takeaways:")
    print("- Intelligent mode uses LLM to understand content structure")
    print("- Single-topic content (tutorials, profiles) → Full doc mode")
    print("- Multi-topic content → Paragraph mode")
    print("- Low-value pages are automatically skipped")
    print("- Better RAG performance by matching mode to content type")

if __name__ == "__main__":
    asyncio.run(main())