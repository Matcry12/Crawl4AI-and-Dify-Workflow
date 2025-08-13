#!/usr/bin/env python3
"""
Test runner for all intelligent RAG mode tests.
Run this to see all different modes in action.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import test modules
from example_intelligent_mode import test_intelligent_mode, compare_modes
from example_dual_mode_switch import test_with_word_threshold, test_with_token_threshold

async def run_all_tests():
    """Run all test examples in sequence."""
    print("🚀 Running All Intelligent RAG Mode Tests")
    print("=" * 80)
    print()
    
    tests = [
        ("1. Word Count Threshold Mode", test_with_word_threshold),
        ("2. Token Count Threshold Mode", test_with_token_threshold),
        ("3. Intelligent AI Mode", test_intelligent_mode),
        ("4. Mode Comparison", compare_modes),
    ]
    
    for name, test_func in tests:
        print(f"\n{'='*80}")
        print(f"Running: {name}")
        print(f"{'='*80}\n")
        
        try:
            await test_func()
            print(f"\n✅ {name} - COMPLETED")
        except Exception as e:
            print(f"\n❌ {name} - FAILED: {e}")
            import traceback
            traceback.print_exc()
        
        # Small delay between tests
        await asyncio.sleep(2)
    
    print("\n" + "="*80)
    print("🎉 All tests completed!")
    print("="*80)

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check for required environment variables
    required_vars = ['DIFY_API_KEY', 'GEMINI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these in your .env file or environment")
        sys.exit(1)
    
    # Run all tests
    asyncio.run(run_all_tests())