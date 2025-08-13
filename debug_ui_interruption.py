#!/usr/bin/env python3
"""
Debug script to identify UI interruption issues.
"""

import asyncio
import os
from dotenv import load_dotenv
from crawl_workflow import CrawlWorkflow

async def test_intelligent_mode_minimal():
    """Test minimal intelligent mode to identify interruption point."""
    load_dotenv()
    
    print("🔍 Testing Intelligent Mode for Interruptions")
    print("=" * 60)
    
    # Test with a simple URL
    test_url = "https://httpbin.org/html"
    
    try:
        # Create workflow with intelligent mode
        workflow = CrawlWorkflow(
            dify_base_url="http://localhost:8088",
            dify_api_key=os.getenv('DIFY_API_KEY', 'test-key'),
            gemini_api_key=os.getenv('GEMINI_API_KEY'),
            enable_dual_mode=True,
            use_intelligent_mode=True,
            intelligent_analysis_model="gemini/gemini-1.5-flash"
        )
        
        print(f"\n📍 Testing URL: {test_url}")
        print("This should complete quickly without interruption...")
        
        # Run with minimal settings
        await workflow.crawl_and_process(
            url=test_url,
            max_pages=1,
            max_depth=0,
            extraction_model="gemini/gemini-1.5-flash"  # Use fast model
        )
        
        print("\n✅ Test completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Process was interrupted by user")
    except Exception as e:
        print(f"\n❌ Error occurred: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

async def test_threshold_mode():
    """Test threshold mode to see if it works without interruption."""
    load_dotenv()
    
    print("\n\n🔍 Testing Threshold Mode (Control Test)")
    print("=" * 60)
    
    test_url = "https://httpbin.org/html"
    
    try:
        # Create workflow with threshold mode
        workflow = CrawlWorkflow(
            dify_base_url="http://localhost:8088",
            dify_api_key=os.getenv('DIFY_API_KEY', 'test-key'),
            gemini_api_key=os.getenv('GEMINI_API_KEY'),
            enable_dual_mode=True,
            use_intelligent_mode=False,  # Use threshold mode
            word_threshold=4000
        )
        
        print(f"\n📍 Testing URL: {test_url}")
        print("Using word threshold mode...")
        
        await workflow.crawl_and_process(
            url=test_url,
            max_pages=1,
            max_depth=0,
            extraction_model="gemini/gemini-1.5-flash"
        )
        
        print("\n✅ Test completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Process was interrupted by user")
    except Exception as e:
        print(f"\n❌ Error occurred: {type(e).__name__}: {e}")

def check_environment():
    """Check if environment is properly configured."""
    print("🔧 Checking Environment")
    print("=" * 60)
    
    # Check API keys
    gemini_key = os.getenv('GEMINI_API_KEY')
    dify_key = os.getenv('DIFY_API_KEY')
    
    print(f"✓ GEMINI_API_KEY: {'Set' if gemini_key else 'Missing'}")
    print(f"✓ DIFY_API_KEY: {'Set' if dify_key else 'Missing'}")
    
    if not gemini_key:
        print("\n⚠️ GEMINI_API_KEY is required for intelligent mode!")
        print("  Set it in your .env file or environment")
        return False
    
    return True

async def main():
    """Run all debug tests."""
    load_dotenv()
    
    print("🐛 UI Interruption Debug Tool")
    print("This will help identify where the process is getting interrupted")
    print()
    
    # Check environment first
    if not check_environment():
        return
    
    # Test threshold mode first (should work)
    await test_threshold_mode()
    
    # Then test intelligent mode
    await test_intelligent_mode_minimal()
    
    print("\n\n📊 Debug Summary:")
    print("If threshold mode works but intelligent mode doesn't:")
    print("  → Issue is in the intelligent analyzer")
    print("If both fail:")
    print("  → Issue is in the base crawl workflow")
    print("\nCheck the output above for specific error messages.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user (Ctrl+C)")
        print("This might be the issue you're experiencing in the UI.")
        print("\nPossible causes:")
        print("1. Long-running API calls without timeout")
        print("2. Blocking operations in async code")
        print("3. Resource exhaustion (too many concurrent operations)")