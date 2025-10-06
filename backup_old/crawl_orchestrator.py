"""Crawl orchestration with broken-down methods.

This addresses Issue #9 (Massive Method) by breaking the 465-line
crawl_and_process() method into smaller, manageable pieces.
"""

import logging
import json
import asyncio
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from workflow_config import ProcessingMode
from workflow_utils import normalize_url

logger = logging.getLogger(__name__)


class CrawlOrchestrator:
    """Orchestrates the crawl workflow with separated phases.

    Breaks down the massive crawl_and_process method into logical steps.
    """

    def __init__(self, workflow):
        """Initialize orchestrator with workflow instance.

        Args:
            workflow: CrawlWorkflow instance
        """
        self.workflow = workflow

    async def collect_urls_phase(
        self,
        crawler,
        start_url: str,
        config,
        max_pages: int
    ) -> Tuple[List[str], List[str]]:
        """Phase 1: Collect URLs and check for duplicates.

        Args:
            crawler: AsyncWebCrawler instance
            start_url: Starting URL
            config: Crawler configuration
            max_pages: Maximum pages to crawl

        Returns:
            Tuple of (urls_to_process, duplicate_urls)
        """
        logger.info("\n🔍 Phase 1: Collecting URLs and checking for duplicates...")

        urls_to_process = []
        duplicate_urls = []

        result_stream = await crawler.arun(url=start_url, config=config)
        crawled_count = 0

        try:
            async for page_result in result_stream:
                if hasattr(page_result, 'url'):
                    crawled_count += 1

                    if crawled_count > max_pages:
                        break

                    if page_result.success:
                        exists, kb_id, doc_name = await self._check_duplicate(page_result.url)

                        if exists:
                            duplicate_urls.append(page_result.url)
                            logger.info(f"⏭️  [Page {crawled_count}] {page_result.url}")
                            logger.info(f"    Already exists as: '{doc_name}' in KB: {kb_id}")
                        else:
                            urls_to_process.append(page_result.url)
                            logger.info(f"✅ [Page {crawled_count}] {page_result.url}")
                            logger.info(f"    Will be saved as: '{doc_name}' - New URL to process")

        except Exception as e:
            logger.error(f"\nError during URL collection: {e}")

        # Phase 1 Summary
        logger.info(f"\n📄 Phase 1 Complete:")
        logger.info(f"  Total URLs found: {crawled_count}")
        logger.info(f"  Duplicate URLs skipped: {len(duplicate_urls)}")
        logger.info(f"  New URLs to process: {len(urls_to_process)}")

        return urls_to_process, duplicate_urls

    async def _check_duplicate(self, url: str) -> Tuple[bool, Optional[str], str]:
        """Check if URL already exists.

        Args:
            url: URL to check

        Returns:
            Tuple of (exists, kb_id, doc_name)
        """
        return await self.workflow.check_url_exists(url)

    async def determine_processing_mode(
        self,
        crawler,
        url: str
    ) -> Tuple[Optional[ProcessingMode], Dict, Optional[any]]:
        """Determine which processing mode to use for content.

        Args:
            crawler: AsyncWebCrawler instance
            url: URL to analyze

        Returns:
            Tuple of (processing_mode, mode_analysis, raw_result)
        """
        if not self.workflow.enable_dual_mode:
            # Legacy mode
            mode = ProcessingMode.PARAGRAPH if self.workflow.use_parent_child else None
            return mode, {}, None

        # Manual mode override
        if self.workflow.manual_mode:
            if self.workflow.manual_mode == 'full_doc':
                mode = ProcessingMode.FULL_DOC
            else:
                mode = ProcessingMode.PARAGRAPH
            logger.info(f"  ✋ Manual mode: {mode.value}")
            return mode, {'manual_mode': True}, None

        # Get raw content for analysis
        from crawl4ai.async_configs import CrawlerRunConfig, CacheMode

        logger.info(f"  🔍 Getting raw content for mode analysis...")
        raw_config = CrawlerRunConfig(
            extraction_strategy=None,
            cache_mode=CacheMode.BYPASS
        )
        raw_result = await crawler.arun(url=url, config=raw_config)

        if not raw_result.success or not raw_result.markdown:
            logger.warning(f"  ⚠️  Failed to get raw content, using default mode")
            return ProcessingMode.PARAGRAPH, {}, None

        # Intelligent mode
        if self.workflow.use_intelligent_mode:
            try:
                logger.info(f"  🤖 Running intelligent content analysis...")
                mode, analysis = await self.workflow.content_processor.determine_processing_mode_intelligent(
                    raw_result.markdown, url
                )

                # Check if should skip
                if analysis.get('skip', False):
                    logger.info(f"  ⏭️  Skipping: {analysis.get('skip_reason', 'Low value')}")
                    return None, analysis, raw_result

                logger.info(f"  📊 Intelligent analysis:")
                logger.info(f"     🎯 Content value: {analysis.get('content_value', 'unknown')}")
                logger.info(f"     📋 Structure: {analysis.get('content_structure', 'unknown')}")
                logger.info(f"  📄 Selected mode: {mode.value}")

                return mode, analysis, raw_result

            except Exception as e:
                logger.warning(f"  ⚠️  Intelligent analysis failed: {e}, falling back...")

        # Threshold-based mode selection
        url_suggests_full = self.workflow.content_processor.should_use_full_doc_for_url(url)

        if url_suggests_full:
            mode = ProcessingMode.FULL_DOC
            logger.info(f"  📄 URL pattern suggests full doc mode")
        else:
            mode, analysis = self.workflow.content_processor.determine_processing_mode(raw_result.markdown)
            logger.info(f"  📊 Content analysis:")
            logger.info(f"     📝 Word count: {analysis.get('word_count', 0):,}")
            logger.info(f"     🎯 Token count: {analysis.get('token_count', 0):,}")
            logger.info(f"  📄 Selected mode: {mode.value}")

        return mode, analysis, raw_result

    async def extract_single_url(
        self,
        crawler,
        url: str,
        processing_mode: ProcessingMode,
        extraction_model: str,
        output_dir: Path
    ) -> Tuple[bool, Optional[Dict], Optional[ProcessingMode]]:
        """Extract content from a single URL.

        Args:
            crawler: AsyncWebCrawler instance
            url: URL to extract
            processing_mode: Processing mode to use
            extraction_model: Model for extraction
            output_dir: Directory to save output

        Returns:
            Tuple of (success, extracted_data, processing_mode)
        """
        retry_count = 0
        max_retries = 2

        while retry_count <= max_retries:
            try:
                if retry_count > 0:
                    logger.info(f"  🔄 Retry attempt {retry_count}/{max_retries}...")
                    await asyncio.sleep(2)

                # Create extraction strategy
                extraction_strategy = self.workflow.create_extraction_strategy(
                    processing_mode, extraction_model
                )

                from crawl4ai.async_configs import CrawlerRunConfig, CacheMode
                extraction_config = CrawlerRunConfig(
                    extraction_strategy=extraction_strategy,
                    cache_mode=CacheMode.BYPASS
                )

                # Extract
                result = await crawler.arun(url=url, config=extraction_config)

                if not result.success or not result.extracted_content:
                    logger.warning(f"  ⚠️  Extraction failed: {getattr(result, 'error_message', 'Unknown')}")
                    retry_count += 1
                    continue

                # Parse extracted data
                if isinstance(result.extracted_content, str):
                    extracted_data = json.loads(result.extracted_content)
                else:
                    extracted_data = result.extracted_content

                if isinstance(extracted_data, list):
                    extracted_data = extracted_data[0] if extracted_data else {}

                if not extracted_data or not extracted_data.get('description'):
                    logger.warning(f"  ⚠️  No valid content extracted")
                    retry_count += 1
                    continue

                # Save to file
                self._save_extraction(url, extracted_data, output_dir)

                return True, extracted_data, processing_mode

            except json.JSONDecodeError as e:
                logger.error(f"  ❌ JSON parsing error: {e}")
                retry_count += 1
            except Exception as e:
                logger.error(f"  ❌ Error: {e}")
                retry_count += 1

        return False, None, processing_mode

    def _save_extraction(self, url: str, data: Dict, output_dir: Path) -> str:
        """Save extracted data to JSON file.

        Args:
            url: Source URL
            data: Extracted data
            output_dir: Output directory

        Returns:
            Path to saved file
        """
        url_filename = url.replace("https://", "").replace("http://", "")
        url_filename = url_filename.replace("/", "_").replace("?", "_").replace(":", "_")
        url_filename = url_filename[:100]

        json_file = output_dir / f"{url_filename}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"  💾 Saved: {json_file}")
        return str(json_file)

    def generate_summary(
        self,
        crawled_count: int,
        duplicate_urls: List[str],
        urls_to_process: List[str],
        extraction_failures: int,
        workflow_results: List[Dict],
        extracted_files: List[str]
    ) -> None:
        """Generate and log final summary.

        Args:
            crawled_count: Total URLs discovered
            duplicate_urls: List of duplicate URLs
            urls_to_process: List of URLs to process
            extraction_failures: Number of failed extractions
            workflow_results: List of workflow results
            extracted_files: List of saved files
        """
        logger.info("\n" + "=" * 80)
        logger.info("🎯 INTELLIGENT CRAWL WORKFLOW SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total URLs discovered: {crawled_count}")
        logger.info(f"Duplicate URLs skipped (saved tokens): {len(duplicate_urls)}")
        logger.info(f"New URLs processed: {len(urls_to_process)}")
        logger.info(f"Extraction failures: {extraction_failures}")
        logger.info(f"Total documents saved: {len(extracted_files)}")

        if workflow_results:
            successful = sum(1 for r in workflow_results if r['success'])
            created_new = sum(1 for r in workflow_results if r.get('status') == 'created_new')
            skipped_existing = sum(1 for r in workflow_results if r.get('status') == 'skipped_existing')
            failed = sum(1 for r in workflow_results if not r['success'])

            logger.info(f"Knowledge base operations: {successful}/{len(workflow_results)} successful")
            logger.info(f"  ✅ New documents created: {created_new}")
            logger.info(f"  ⏭️  Existing documents skipped: {skipped_existing}")
            logger.info(f"  ❌ Failed operations: {failed}")

            # Show knowledge bases
            logger.info(f"\n📚 Knowledge bases: {len(self.workflow.knowledge_bases)}")
            for name, kb_id in self.workflow.knowledge_bases.items():
                logger.info(f"  • {name} (ID: {kb_id})")

            # Show documents cached
            total_docs = sum(len(docs) for docs in self.workflow.document_cache.values())
            logger.info(f"\n📄 Total documents tracked: {total_docs}")
