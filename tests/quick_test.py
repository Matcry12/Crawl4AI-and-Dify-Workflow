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

    # Test 6: Dual-mode selection
    logger.info("\n✓ Test 6: Dual-Mode Selection")
    from core.content_processor import ProcessingMode
    short_content = "word " * 2000  # 2000 words
    mode1, analysis1 = workflow.content_processor.determine_processing_mode(short_content)
    logger.info(f"  Short content ({analysis1['word_count']} words) → {mode1.value}")

    long_content = "word " * 5000  # 5000 words
    mode2, analysis2 = workflow.content_processor.determine_processing_mode(long_content)
    logger.info(f"  Long content ({analysis2['word_count']} words) → {mode2.value}")
    assert mode1 == ProcessingMode.FULL_DOC, "Short content should use FULL_DOC"
    assert mode2 == ProcessingMode.PARAGRAPH, "Long content should use PARAGRAPH"

    # Test 7: Connection pooling
    logger.info("\n✓ Test 7: Connection Pooling")
    logger.info(f"  Pooling enabled: {workflow.dify_api.enable_connection_pooling}")
    logger.info(f"  Session exists: {workflow.dify_api.session is not None}")

    # Test with pooling disabled
    workflow_no_pool = CrawlWorkflow(
        dify_base_url=os.getenv('DIFY_BASE_URL', 'http://localhost:8088'),
        dify_api_key=os.getenv('DIFY_API_KEY'),
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        enable_connection_pooling=False
    )
    logger.info(f"  No pooling - Pooling enabled: {workflow_no_pool.dify_api.enable_connection_pooling}")
    logger.info(f"  No pooling - Session exists: {workflow_no_pool.dify_api.session is not None}")
    assert workflow.dify_api.session is not None, "Pooling should create session"
    assert workflow_no_pool.dify_api.session is None, "No pooling should not create session"

    # Test 8: Retry and Circuit Breaker flags
    logger.info("\n✓ Test 8: Resilience Flags")
    logger.info(f"  Retry enabled: {workflow.dify_api.enable_retry}")
    logger.info(f"  Circuit breaker enabled: {workflow.dify_api.enable_circuit_breaker}")
    logger.info(f"  Circuit breakers: {list(workflow.dify_api.circuit_breakers.keys())}")
    assert workflow.dify_api.enable_retry is True, "Retry should be enabled"
    assert workflow.dify_api.enable_circuit_breaker is True, "Circuit breaker should be enabled"

    logger.info("\n" + "="*80)
    logger.info("✅ ALL QUICK TESTS PASSED (8 tests)")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(quick_test())
