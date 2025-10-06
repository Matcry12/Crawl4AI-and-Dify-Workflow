#!/usr/bin/env python3
"""Test script to verify metadata integration in the crawl workflow."""

import asyncio
import os
from dotenv import load_dotenv
from crawl_workflow import CrawlWorkflow

async def test_metadata_integration():
    """Test that metadata is properly created and assigned."""
    load_dotenv(override=True)

    # Initialize workflow
    workflow = CrawlWorkflow(
        dify_base_url=os.getenv('DIFY_BASE_URL', 'http://localhost:8088'),
        dify_api_key=os.getenv('DIFY_API_KEY'),
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        enable_dual_mode=True,
        word_threshold=4000,
        naming_model="gemini/gemini-1.5-flash"
    )

    # Initialize to load knowledge bases
    await workflow.initialize()

    # Test with a single URL
    print("\n" + "="*80)
    print("🧪 TESTING METADATA INTEGRATION")
    print("="*80)

    test_url = "https://docs.eosnetwork.com/quick-start"

    print(f"\n📋 Test Configuration:")
    print(f"  URL: {test_url}")
    print(f"  Max pages: 1")
    print(f"  Metadata fields to create: source_url, crawl_date, domain, content_type, processing_mode, word_count")

    # Run crawl
    await workflow.crawl_and_process(
        url=test_url,
        max_pages=1,
        max_depth=0,
        extraction_model="gemini/gemini-2.0-flash-exp"
    )

    print("\n" + "="*80)
    print("✅ TEST COMPLETE")
    print("="*80)
    print("\nMetadata should now be visible in Dify Knowledge Base UI.")
    print("Check the document details to see the assigned metadata fields.")

if __name__ == "__main__":
    asyncio.run(test_metadata_integration())
