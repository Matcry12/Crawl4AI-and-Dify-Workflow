#!/usr/bin/env python3
"""
Compare flat vs parent-child chunking modes
"""

import asyncio
from crawl_workflow import CrawlWorkflow
import os
from dotenv import load_dotenv

async def compare_chunking_modes():
    """Compare the results of flat vs parent-child chunking."""
    
    load_dotenv(override=True)
    
    # Test URL
    test_url = "https://docs.python.org/3/tutorial/introduction.html"
    
    print("🔬 CHUNKING MODE COMPARISON")
    print("=" * 80)
    
    # Test 1: Flat chunking
    print("\n1️⃣ FLAT CHUNKING MODE")
    print("-" * 40)
    
    flat_workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key="dataset-VoYPMEaQ8L1udk2F6oek99XK",
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        use_parent_child=False  # Flat chunking
    )
    
    print("Configuration:")
    print("  - Mode: Flat chunking")
    print("  - Separator: ###SECTION_BREAK###")
    print("  - Creates: Single-level chunks")
    print("  - Best for: Simple content, linear documentation")
    
    # Test 2: Parent-child chunking
    print("\n2️⃣ PARENT-CHILD CHUNKING MODE")
    print("-" * 40)
    
    parent_child_workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key="dataset-VoYPMEaQ8L1udk2F6oek99XK",
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        use_parent_child=True  # Parent-child chunking
    )
    
    print("Configuration:")
    print("  - Mode: Parent-child hierarchical chunking")
    print("  - Parent separator: ###PARENT_SECTION###")
    print("  - Child separator: ###CHILD_SECTION###")
    print("  - Creates: Two-level hierarchy")
    print("  - Best for: Complex documentation, tutorials, guides")
    
    print("\n" + "=" * 80)
    print("📋 KEY DIFFERENCES:")
    print("=" * 80)
    
    print("\n🔸 FLAT CHUNKING:")
    print("  ✓ Simpler structure")
    print("  ✓ Each chunk is independent")
    print("  ✓ Good for straightforward content")
    print("  ✗ May lose context between related sections")
    print("  ✗ Difficult to maintain topic hierarchy")
    
    print("\n🔸 PARENT-CHILD CHUNKING:")
    print("  ✓ Maintains topic hierarchy")
    print("  ✓ Parents provide overview and context")
    print("  ✓ Children contain detailed information")
    print("  ✓ Better for complex, structured content")
    print("  ✓ Allows both high-level and detailed retrieval")
    print("  ✗ More complex to set up")
    print("  ✗ Requires careful content organization")
    
    print("\n📊 WHEN TO USE EACH:")
    print("-" * 40)
    
    print("\nUse FLAT chunking for:")
    print("  • Blog posts")
    print("  • News articles")
    print("  • Simple FAQs")
    print("  • Linear documentation")
    
    print("\nUse PARENT-CHILD chunking for:")
    print("  • Technical documentation")
    print("  • Tutorials and guides")
    print("  • API documentation")
    print("  • Complex how-to content")
    print("  • Multi-step processes")
    
    print("\n💡 EXAMPLE STRUCTURE:")
    print("-" * 40)
    
    print("\nFlat chunking output:")
    print("```")
    print("[Introduction to Python]")
    print("Content about Python basics...")
    print("###SECTION_BREAK###")
    print("[Variables and Data Types]")
    print("Content about variables...")
    print("###SECTION_BREAK###")
    print("[Control Flow]")
    print("Content about if/else...")
    print("```")
    
    print("\nParent-child chunking output:")
    print("```")
    print("###PARENT_SECTION###[Python Fundamentals Overview]")
    print("High-level overview of Python basics...")
    print("###CHILD_SECTION###[Variables and Basic Data Types]")
    print("Detailed info about int, str, float...")
    print("###CHILD_SECTION###[Complex Data Structures]")
    print("Detailed info about lists, dicts...")
    print("###PARENT_SECTION###[Control Flow and Functions]")
    print("Overview of program flow concepts...")
    print("###CHILD_SECTION###[Conditional Statements]")
    print("Detailed if/else examples...")
    print("###CHILD_SECTION###[Loops and Iteration]")
    print("Detailed for/while examples...")
    print("```")
    
    print("\n✅ Both workflows are now configured and ready to use!")
    print("Run crawl_workflow.py with use_parent_child=True/False to test each mode.")

if __name__ == "__main__":
    asyncio.run(compare_chunking_modes())