"""
Comprehensive Test Suite for Crawl Workflow
Tests all features: crawling, extraction, resilience, dual-mode processing
"""

import asyncio
import json
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.crawl_workflow import CrawlWorkflow
from core.resilience_utils import CrawlCheckpoint, FailureQueue
from core.content_processor import ProcessingMode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestCrawlWorkflow:
    """Test suite for crawl workflow"""

    def __init__(self):
        load_dotenv(override=True)
        self.dify_base_url = os.getenv('DIFY_BASE_URL', 'http://localhost:8088')
        self.dify_api_key = os.getenv('DIFY_API_KEY')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.test_results = []

    def log_test_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = {
            'test': test_name,
            'passed': passed,
            'message': message
        }
        self.test_results.append(result)
        logger.info(f"{status} - {test_name}: {message}")

    async def test_1_initialization(self):
        """Test 1: Basic initialization"""
        logger.info("\n" + "="*80)
        logger.info("TEST 1: Basic Initialization")
        logger.info("="*80)

        try:
            workflow = CrawlWorkflow(
                dify_base_url=self.dify_base_url,
                dify_api_key=self.dify_api_key,
                gemini_api_key=self.gemini_api_key,
                enable_resilience=True
            )

            # Check initialization
            assert workflow.dify_api is not None, "Dify API not initialized"
            assert workflow.checkpoint is not None, "Checkpoint not initialized"
            assert workflow.failure_queue is not None, "Failure queue not initialized"
            assert workflow.content_processor is not None, "Content processor not initialized"

            await workflow.initialize()
            assert workflow._initialized is True, "Workflow not initialized"

            self.log_test_result("test_1_initialization", True, "All components initialized")
            return True

        except Exception as e:
            self.log_test_result("test_1_initialization", False, str(e))
            return False

    async def test_2_knowledge_base_creation(self):
        """Test 2: Knowledge base creation and caching"""
        logger.info("\n" + "="*80)
        logger.info("TEST 2: Knowledge Base Creation")
        logger.info("="*80)

        try:
            workflow = CrawlWorkflow(
                dify_base_url=self.dify_base_url,
                dify_api_key=self.dify_api_key,
                gemini_api_key=self.gemini_api_key
            )

            await workflow.initialize()

            # Test KB creation
            test_category = f"test_kb_{int(asyncio.get_event_loop().time())}"
            kb_id = await workflow.ensure_knowledge_base_exists(test_category)

            assert kb_id is not None, "KB ID is None"
            assert test_category in workflow.knowledge_bases, "KB not in cache"
            assert workflow.knowledge_bases[test_category] == kb_id, "KB ID mismatch"

            # Test KB reuse (should return same ID)
            kb_id_2 = await workflow.ensure_knowledge_base_exists(test_category)
            assert kb_id == kb_id_2, "KB not reused from cache"

            self.log_test_result("test_2_knowledge_base_creation", True,
                               f"KB created and cached: {kb_id}")
            return True

        except Exception as e:
            self.log_test_result("test_2_knowledge_base_creation", False, str(e))
            return False

    async def test_3_document_name_generation(self):
        """Test 3: Document name generation consistency"""
        logger.info("\n" + "="*80)
        logger.info("TEST 3: Document Name Generation")
        logger.info("="*80)

        try:
            workflow = CrawlWorkflow(
                dify_base_url=self.dify_base_url,
                dify_api_key=self.dify_api_key,
                gemini_api_key=self.gemini_api_key
            )

            # Test URL normalization
            url1 = "https://example.com/docs/api"
            url2 = "https://example.com/docs/api/"  # With trailing slash

            name1 = workflow.generate_document_name(url1)
            name2 = workflow.generate_document_name(url2)

            assert name1 == name2, f"Names don't match: {name1} != {name2}"

            # Test with title (should be ignored for consistency)
            name3 = workflow.generate_document_name(url1, "Some Title")
            assert name1 == name3, "Title affects document name"

            # Test different URLs generate different names
            url3 = "https://example.com/docs/guide"
            name4 = workflow.generate_document_name(url3)
            assert name1 != name4, "Different URLs generate same name"

            self.log_test_result("test_3_document_name_generation", True,
                               f"Generated name: {name1}")
            return True

        except Exception as e:
            self.log_test_result("test_3_document_name_generation", False, str(e))
            return False

    async def test_4_duplicate_detection(self):
        """Test 4: Duplicate URL detection"""
        logger.info("\n" + "="*80)
        logger.info("TEST 4: Duplicate Detection")
        logger.info("="*80)

        try:
            workflow = CrawlWorkflow(
                dify_base_url=self.dify_base_url,
                dify_api_key=self.dify_api_key,
                gemini_api_key=self.gemini_api_key
            )

            await workflow.initialize()

            test_url = "https://example.com/test-page"

            # First check - should not exist
            exists1, kb_id1, doc_name1 = await workflow.check_url_exists(test_url)
            assert exists1 is False, "URL incorrectly marked as existing"

            # Simulate adding to cache
            if kb_id1:
                if kb_id1 not in workflow.document_cache:
                    workflow.document_cache[kb_id1] = {}
                workflow.document_cache[kb_id1][doc_name1] = "test_doc_id"

                # Second check - should exist now
                exists2, kb_id2, doc_name2 = await workflow.check_url_exists(test_url)
                assert exists2 is True, "URL not detected in cache"
                assert doc_name1 == doc_name2, "Document names don't match"

            self.log_test_result("test_4_duplicate_detection", True,
                               f"Duplicate detection working")
            return True

        except Exception as e:
            self.log_test_result("test_4_duplicate_detection", False, str(e))
            return False

    async def test_5_checkpoint_system(self):
        """Test 5: Checkpoint save/load functionality"""
        logger.info("\n" + "="*80)
        logger.info("TEST 5: Checkpoint System")
        logger.info("="*80)

        try:
            checkpoint_file = "test_checkpoint.json"

            # Clean up first
            if Path(checkpoint_file).exists():
                Path(checkpoint_file).unlink()

            # Create checkpoint
            checkpoint = CrawlCheckpoint(checkpoint_file)
            checkpoint.initialize("https://example.com/test", total_urls=10)

            # Add some data
            checkpoint.add_pending(["url1", "url2", "url3"])
            checkpoint.mark_processed("url1", success=True)
            checkpoint.mark_failed("url2", "Test error")
            checkpoint.save()

            # Verify file exists
            assert Path(checkpoint_file).exists(), "Checkpoint file not created"

            # Load checkpoint in new instance
            checkpoint2 = CrawlCheckpoint(checkpoint_file)
            loaded = checkpoint2.load()

            assert loaded is True, "Checkpoint not loaded"
            assert len(checkpoint2.state['processed_urls']) == 2, "Wrong processed count"
            assert "url1" in checkpoint2.state['processed_urls'], "url1 not in processed"
            assert "url2" in checkpoint2.state['failed_urls'], "url2 not in failed"
            assert len(checkpoint2.state['pending_urls']) == 1, "Wrong pending count"

            stats = checkpoint2.get_statistics()
            assert stats['successful'] == 1, "Wrong successful count"
            assert stats['failed'] == 1, "Wrong failed count"

            # Clean up
            Path(checkpoint_file).unlink()

            self.log_test_result("test_5_checkpoint_system", True,
                               "Checkpoint save/load works")
            return True

        except Exception as e:
            self.log_test_result("test_5_checkpoint_system", False, str(e))
            # Clean up on error
            if Path(checkpoint_file).exists():
                Path(checkpoint_file).unlink()
            return False

    async def test_6_failure_queue(self):
        """Test 6: Failure queue functionality"""
        logger.info("\n" + "="*80)
        logger.info("TEST 6: Failure Queue")
        logger.info("="*80)

        try:
            queue_file = "test_failure_queue.json"

            # Clean up first
            if Path(queue_file).exists():
                Path(queue_file).unlink()

            # Create failure queue
            queue = FailureQueue(queue_file)

            # Add failures
            queue.add("url1", "Connection timeout")
            queue.add("url2", "HTTP 500")
            queue.add("url3", "Parse error")

            assert len(queue.failures) == 3, "Wrong failure count"

            # Test retryable
            retryable = queue.get_retryable(max_retries=3)
            assert len(retryable) == 3, "All should be retryable"

            # Mark one as retried
            queue.mark_retried("url1")
            assert queue.failures[0]['retry_count'] == 1, "Retry count not updated"

            # Remove one
            queue.remove("url2")
            assert len(queue.failures) == 2, "URL not removed"

            # Export report
            report_file = "test_failure_report.json"
            queue.export_report(report_file)
            assert Path(report_file).exists(), "Report not created"

            # Clean up
            Path(queue_file).unlink()
            Path(report_file).unlink()

            self.log_test_result("test_6_failure_queue", True,
                               "Failure queue works correctly")
            return True

        except Exception as e:
            self.log_test_result("test_6_failure_queue", False, str(e))
            # Clean up on error
            for f in [queue_file, "test_failure_report.json"]:
                if Path(f).exists():
                    Path(f).unlink()
            return False

    async def test_7_single_page_crawl(self):
        """Test 7: Crawl single page (real test)"""
        logger.info("\n" + "="*80)
        logger.info("TEST 7: Single Page Crawl (Real)")
        logger.info("="*80)

        try:
            workflow = CrawlWorkflow(
                dify_base_url=self.dify_base_url,
                dify_api_key=self.dify_api_key,
                gemini_api_key=self.gemini_api_key,
                enable_resilience=True,
                checkpoint_file="test_crawl_checkpoint.json"
            )

            # Crawl a simple, reliable page
            test_url = "https://example.com"

            await workflow.crawl_and_process(
                url=test_url,
                max_pages=1,
                max_depth=0,
                extraction_model="gemini/gemini-2.0-flash-exp"
            )

            # Check that checkpoint was created
            assert Path("test_crawl_checkpoint.json").exists(), "Checkpoint not created"

            # Check stats
            stats = workflow.checkpoint.get_statistics()
            logger.info(f"Stats: {stats}")

            # Clean up
            Path("test_crawl_checkpoint.json").unlink()
            if Path("failure_queue.json").exists():
                Path("failure_queue.json").unlink()

            self.log_test_result("test_7_single_page_crawl", True,
                               f"Crawled {stats.get('total_urls', 0)} URLs")
            return True

        except Exception as e:
            self.log_test_result("test_7_single_page_crawl", False, str(e))
            # Clean up on error
            for f in ["test_crawl_checkpoint.json", "failure_queue.json"]:
                if Path(f).exists():
                    Path(f).unlink()
            return False

    async def test_8_dual_mode_selection(self):
        """Test 8: Dual-mode processing selection"""
        logger.info("\n" + "="*80)
        logger.info("TEST 8: Dual-Mode Selection")
        logger.info("="*80)

        try:
            workflow = CrawlWorkflow(
                dify_base_url=self.dify_base_url,
                dify_api_key=self.dify_api_key,
                gemini_api_key=self.gemini_api_key,
                enable_dual_mode=True,
                word_threshold=4000
            )

            # Test short content (should use FULL_DOC)
            short_content = "word " * 2000  # 2000 words
            mode1, analysis1 = workflow.content_processor.determine_processing_mode(short_content)
            assert mode1 == ProcessingMode.FULL_DOC, f"Short content should use FULL_DOC, got {mode1}"

            # Test long content (should use PARAGRAPH)
            long_content = "word " * 5000  # 5000 words
            mode2, analysis2 = workflow.content_processor.determine_processing_mode(long_content)
            assert mode2 == ProcessingMode.PARAGRAPH, f"Long content should use PARAGRAPH, got {mode2}"

            logger.info(f"Short content ({analysis1['word_count']} words) → {mode1.value}")
            logger.info(f"Long content ({analysis2['word_count']} words) → {mode2.value}")

            self.log_test_result("test_8_dual_mode_selection", True,
                               "Mode selection working correctly")
            return True

        except Exception as e:
            self.log_test_result("test_8_dual_mode_selection", False, str(e))
            return False

    async def test_9_metadata_fields(self):
        """Test 9: Metadata field creation"""
        logger.info("\n" + "="*80)
        logger.info("TEST 9: Metadata Fields")
        logger.info("="*80)

        try:
            workflow = CrawlWorkflow(
                dify_base_url=self.dify_base_url,
                dify_api_key=self.dify_api_key,
                gemini_api_key=self.gemini_api_key
            )

            await workflow.initialize()

            # Get or create a test KB
            test_kb = f"test_metadata_kb_{int(asyncio.get_event_loop().time())}"
            kb_id = await workflow.ensure_knowledge_base_exists(test_kb)

            if kb_id:
                # Ensure metadata fields
                metadata_fields = await workflow.ensure_metadata_fields(kb_id)

                # Check required fields exist
                required_fields = ['source_url', 'crawl_date', 'domain', 'content_type',
                                 'processing_mode', 'word_count']

                for field in required_fields:
                    assert field in metadata_fields, f"Missing field: {field}"
                    assert 'id' in metadata_fields[field], f"Field {field} has no ID"
                    assert 'type' in metadata_fields[field], f"Field {field} has no type"

                logger.info(f"Created/verified {len(metadata_fields)} metadata fields")

                self.log_test_result("test_9_metadata_fields", True,
                                   f"{len(metadata_fields)} fields verified")
                return True
            else:
                self.log_test_result("test_9_metadata_fields", False,
                                   "Could not create KB")
                return False

        except Exception as e:
            self.log_test_result("test_9_metadata_fields", False, str(e))
            return False

    async def test_10_category_normalization(self):
        """Test 10: Category name normalization"""
        logger.info("\n" + "="*80)
        logger.info("TEST 10: Category Normalization")
        logger.info("="*80)

        try:
            workflow = CrawlWorkflow(
                dify_base_url=self.dify_base_url,
                dify_api_key=self.dify_api_key,
                gemini_api_key=self.gemini_api_key
            )

            # Test various category formats that should normalize to same value
            test_cases = [
                ("EOS Network", "eos"),
                ("eos_network", "eos"),
                ("eos-network", "eos"),
                ("React JS", "react"),
                ("reactjs", "react"),
                ("react.js", "react"),
            ]

            for input_cat, expected in test_cases:
                normalized = workflow.preprocess_category_name(input_cat)
                assert normalized == expected, f"{input_cat} → {normalized}, expected {expected}"
                logger.info(f"✓ '{input_cat}' → '{normalized}'")

            self.log_test_result("test_10_category_normalization", True,
                               f"All {len(test_cases)} normalizations correct")
            return True

        except Exception as e:
            self.log_test_result("test_10_category_normalization", False, str(e))
            return False

    async def run_all_tests(self):
        """Run all tests"""
        logger.info("\n" + "#"*80)
        logger.info("# STARTING COMPREHENSIVE TEST SUITE")
        logger.info("#"*80)

        tests = [
            self.test_1_initialization,
            self.test_2_knowledge_base_creation,
            self.test_3_document_name_generation,
            self.test_4_duplicate_detection,
            self.test_5_checkpoint_system,
            self.test_6_failure_queue,
            self.test_7_single_page_crawl,
            self.test_8_dual_mode_selection,
            self.test_9_metadata_fields,
            self.test_10_category_normalization,
        ]

        for test in tests:
            try:
                await test()
            except Exception as e:
                logger.error(f"Test crashed: {test.__name__}: {e}")
                self.log_test_result(test.__name__, False, f"Crashed: {e}")

        # Summary
        logger.info("\n" + "#"*80)
        logger.info("# TEST SUMMARY")
        logger.info("#"*80)

        passed = sum(1 for r in self.test_results if r['passed'])
        failed = len(self.test_results) - passed

        logger.info(f"Total tests: {len(self.test_results)}")
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"Success rate: {passed/len(self.test_results)*100:.1f}%")

        # Show failed tests
        if failed > 0:
            logger.info("\nFailed tests:")
            for result in self.test_results:
                if not result['passed']:
                    logger.info(f"  ❌ {result['test']}: {result['message']}")

        # Save results
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
        os.makedirs(output_dir, exist_ok=True)
        results_path = os.path.join(output_dir, 'test_results.json')

        with open(results_path, "w") as f:
            json.dump({
                'timestamp': asyncio.get_event_loop().time(),
                'total': len(self.test_results),
                'passed': passed,
                'failed': failed,
                'results': self.test_results
            }, f, indent=2)

        logger.info(f"\n✅ Test results saved to: {results_path}")

        return passed == len(self.test_results)


async def main():
    """Main test runner"""
    tester = TestCrawlWorkflow()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
