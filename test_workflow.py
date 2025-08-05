#!/usr/bin/env python3
"""Test the crawl workflow to ensure it works properly."""

import asyncio
import os
from dotenv import load_dotenv

# Test the workflow
async def test_workflow():
    # Load environment variables
    load_dotenv(override=True)
    
    # Check for required API keys
    gemini_key = os.getenv('GEMINI_API_KEY')
    if not gemini_key:
        print("❌ Error: GEMINI_API_KEY not found in environment variables")
        print("Please set GEMINI_API_KEY in your .env file or environment")
        return
    
    print("✅ GEMINI_API_KEY found")
    
    # Import the workflow
    try:
        from crawl_workflow import CrawlWorkflow
        print("✅ Successfully imported CrawlWorkflow")
    except ImportError as e:
        print(f"❌ Failed to import CrawlWorkflow: {e}")
        return
    
    # Initialize workflow with test parameters
    print("\n🔧 Initializing workflow...")
    workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key="dataset-VoYPMEaQ8L1udk2F6oek99XK",  # Replace with your actual key
        gemini_api_key=gemini_key
    )
    
    # Test categorization
    print("\n🧪 Testing categorization...")
    test_content = "This is a Python tutorial about machine learning and artificial intelligence."
    test_url = "https://docs.python.org/tutorial"
    category, tags = workflow.categorize_content(test_content, test_url)
    print(f"  Category: {category}")
    print(f"  Tags: {tags}")
    
    # Run a minimal crawl test
    print("\n🚀 Running minimal crawl test...")
    try:
        await workflow.crawl_and_process(
            url="https://growagarden.fandom.com/wiki/Squirrel",
            max_pages=1,
            max_depth=0  # Don't go deep, just test the main page
        )
        print("✅ Workflow completed successfully!")
    except Exception as e:
        print(f"❌ Workflow failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔍 Testing Crawl Workflow...")
    print("=" * 50)
    asyncio.run(test_workflow())