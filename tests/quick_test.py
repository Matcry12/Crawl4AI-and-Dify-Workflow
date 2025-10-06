"""
Quick Test Script - Rapid validation of core features
Run this for fast feedback during development
"""

import asyncio
import os
import logging
from dotenv import load_dotenv
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.crawl_workflow import CrawlWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def quick_test():
    """Quick test of core functionality"""

    load_dotenv(override=True)

    logger.info("="*80)
    logger.info("QUICK TEST - Core Functionality")
    logger.info("="*80)

    # Test 1: Initialization
    logger.info("\n✓ Test 1: Initialization")
    workflow = CrawlWorkflow(
        dify_base_url=os.getenv('DIFY_BASE_URL', 'http://localhost:8088'),
        dify_api_key=os.getenv('DIFY_API_KEY'),
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        enable_resilience=True
    )
    await workflow.initialize()
    logger.info(f"  Knowledge bases cached: {len(workflow.knowledge_bases)}")

    # Test 2: Document naming
    logger.info("\n✓ Test 2: Document Naming")
    url1 = "https://example.com/docs/api"
    url2 = "https://example.com/docs/api/"
    name1 = workflow.generate_document_name(url1)
    name2 = workflow.generate_document_name(url2)
    assert name1 == name2, "URL normalization failed"
    logger.info(f"  Generated name: {name1}")

    # Test 3: Category normalization
    logger.info("\n✓ Test 3: Category Normalization")
    test_categories = [
        ("EOS Network", "eos"),
        ("React JS", "react"),
    ]
    for input_cat, expected in test_categories:
        result = workflow.preprocess_category_name(input_cat)
        assert result == expected, f"Expected {expected}, got {result}"
        logger.info(f"  '{input_cat}' → '{result}'")

    # Test 4: Checkpoint
    logger.info("\n✓ Test 4: Checkpoint System")
    workflow.checkpoint.initialize("https://example.com", 10)
    workflow.checkpoint.add_pending(["url1", "url2"])
    workflow.checkpoint.mark_processed("url1", success=True)
    stats = workflow.checkpoint.get_statistics()
    logger.info(f"  Stats: {stats}")

    # Test 5: Failure queue
    logger.info("\n✓ Test 5: Failure Queue")
    workflow.failure_queue.add("failed_url", "Test error")
    retryable = workflow.failure_queue.get_retryable()
    logger.info(f"  Retryable failures: {len(retryable)}")

    logger.info("\n" + "="*80)
    logger.info("✅ ALL QUICK TESTS PASSED")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(quick_test())
