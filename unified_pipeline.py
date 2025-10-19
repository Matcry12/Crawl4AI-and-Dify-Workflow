#!/usr/bin/env python3
"""
Unified Pipeline - Combining Old Crawling with New Dual-Mode Processing

This pipeline connects:
1. Crawl system (from crawl_workflow.py) - for web crawling and topic extraction
2. Dual-mode system (from core/*) - for intelligent merging, formatting, and embedding

Flow:
    Crawl URL → Extract Topics → Merge (Dual-Mode) → Embed (Gemini) → Save (PostgreSQL)

Optional: Save to Dify Knowledge Base (for later when local system works well)
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
from dotenv import load_dotenv

# Import old system (crawling)
from core.topic_extractor import TopicExtractor

# Import new system (dual-mode processing)
from core.document_merger import DocumentMerger
from core.natural_formatter import NaturalFormatter
from core.page_processor import PageProcessor
from core.gemini_embeddings import GeminiEmbeddings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class UnifiedPipeline:
    """
    Unified pipeline that combines:
    - Old system: Crawling + Topic Extraction
    - New system: Dual-Mode Merging + Gemini Embeddings + PostgreSQL
    """

    def __init__(
        self,
        db_config: Dict,
        gemini_api_key: Optional[str] = None,
        save_to_dify: bool = False,
        dify_api_key: Optional[str] = None,
        dify_base_url: str = "http://localhost:8088"
    ):
        """
        Initialize unified pipeline.

        Args:
            db_config: PostgreSQL database configuration
            gemini_api_key: Gemini API key for embeddings and extraction
            save_to_dify: Whether to also save to Dify KB (for later)
            dify_api_key: Dify API key (if save_to_dify=True)
            dify_base_url: Dify base URL (if save_to_dify=True)
        """
        self.db_config = db_config
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        self.save_to_dify = save_to_dify

        # Initialize components
        logger.info("🔧 Initializing unified pipeline components...")

        # Old system components
        self.topic_extractor = TopicExtractor(api_key=self.gemini_api_key)
        logger.info("  ✅ TopicExtractor initialized")

        # New system components
        self.formatter = NaturalFormatter()
        self.merger = DocumentMerger()
        self.processor = PageProcessor(db_config=db_config)
        logger.info("  ✅ NaturalFormatter initialized")
        logger.info("  ✅ DocumentMerger initialized")
        logger.info("  ✅ PageProcessor initialized")

        # Dify integration (for later)
        if save_to_dify:
            logger.info("  ⏸️  Dify integration: Enabled (placeholder for later)")
            self.dify_api_key = dify_api_key
            self.dify_base_url = dify_base_url
        else:
            logger.info("  ⏸️  Dify integration: Disabled")

        logger.info("✅ Unified pipeline ready!")

    async def crawl_page(self, url: str) -> Optional[str]:
        """
        Crawl a single page and return markdown content.

        Args:
            url: URL to crawl

        Returns:
            Markdown content or None if failed
        """
        logger.info(f"🌐 Crawling: {url}")

        try:
            browser_config = BrowserConfig(headless=True, verbose=False)

            async with AsyncWebCrawler(config=browser_config) as crawler:
                config = CrawlerRunConfig(
                    extraction_strategy=None,
                    cache_mode=CacheMode.BYPASS
                )

                result = await crawler.arun(url=url, config=config)

                if result.success and result.markdown:
                    logger.info(f"  ✅ Crawled successfully: {len(result.markdown)} characters")
                    return result.markdown
                else:
                    logger.error(f"  ❌ Crawl failed: {getattr(result, 'error_message', 'Unknown error')}")
                    return None

        except Exception as e:
            logger.error(f"  ❌ Crawl error: {e}")
            return None

    async def extract_topics(self, markdown_content: str, source_url: str) -> List[Dict]:
        """
        Extract topics from markdown content using LLM.

        Args:
            markdown_content: Markdown content to extract from
            source_url: Source URL for context

        Returns:
            List of topic dictionaries
        """
        logger.info(f"🔍 Extracting topics from content...")

        try:
            topics = await self.topic_extractor.extract_topics_async(
                markdown_content,
                source_url
            )

            if topics:
                logger.info(f"  ✅ Extracted {len(topics)} topics")
                for i, topic in enumerate(topics, 1):
                    logger.info(f"    {i}. {topic.get('title', 'Untitled')} ({topic.get('category', 'general')})")
                return topics
            else:
                logger.warning(f"  ⚠️  No topics extracted")
                return []

        except Exception as e:
            logger.error(f"  ❌ Topic extraction error: {e}")
            return []

    def merge_and_format_dual_mode(self, topics: List[Dict]) -> List[Dict]:
        """
        Merge topics and create dual-mode documents.

        Args:
            topics: List of topic dictionaries

        Returns:
            List of dual-mode documents
        """
        logger.info(f"🔄 Merging topics into dual-mode documents...")

        try:
            # Use the new dual-mode merger
            documents = self.merger.merge_topics_dual_mode(topics)

            logger.info(f"  ✅ Created {len(documents)} documents (dual-mode)")

            # Show breakdown
            full_doc_count = sum(1 for d in documents if d['mode'] == 'full_doc')
            paragraph_count = sum(1 for d in documents if d['mode'] == 'paragraph')

            logger.info(f"    • Full-doc: {full_doc_count}")
            logger.info(f"    • Paragraph: {paragraph_count}")

            return documents

        except Exception as e:
            logger.error(f"  ❌ Merge error: {e}")
            return []

    async def save_to_postgresql(self, documents: List[Dict], source_url: str) -> Dict:
        """
        Save documents to PostgreSQL with embeddings.

        Args:
            documents: List of document dictionaries
            source_url: Source URL

        Returns:
            Result dictionary with statistics
        """
        logger.info(f"💾 Saving {len(documents)} documents to PostgreSQL...")

        try:
            result = await self.processor.save_documents_batch(documents, source_url)

            logger.info(f"  ✅ Saved {result.get('documents_created', 0)} documents")
            logger.info(f"    • Full-doc: {result.get('mode_distribution', {}).get('full_doc', 0)}")
            logger.info(f"    • Paragraph: {result.get('mode_distribution', {}).get('paragraph', 0)}")

            return result

        except Exception as e:
            logger.error(f"  ❌ Save error: {e}")
            return {'success': False, 'error': str(e)}

    async def save_to_dify_placeholder(self, topics: List[Dict], source_url: str):
        """
        Placeholder for Dify Knowledge Base upload.
        To be implemented later when local system works well.

        Args:
            topics: List of topic dictionaries
            source_url: Source URL
        """
        logger.info(f"⏸️  Dify upload: Placeholder (not implemented yet)")
        logger.info(f"   When implemented, will upload {len(topics)} topics to Dify KB")
        logger.info(f"   Source: {source_url}")
        # TODO: Implement Dify KB upload using DifyAPI from crawl_workflow.py

    async def process_url(self, url: str) -> Dict:
        """
        Complete pipeline: Crawl → Extract → Merge → Save

        Args:
            url: URL to process

        Returns:
            Result dictionary
        """
        logger.info("=" * 80)
        logger.info(f"🚀 UNIFIED PIPELINE: Processing {url}")
        logger.info("=" * 80)

        result = {
            'url': url,
            'success': False,
            'timestamp': datetime.now().isoformat(),
            'steps': {}
        }

        # Step 1: Crawl page
        logger.info("\n📍 Step 1: Crawling page...")
        markdown_content = await self.crawl_page(url)

        if not markdown_content:
            logger.error("❌ Pipeline failed: Crawl error")
            result['error'] = 'Crawl failed'
            return result

        result['steps']['crawl'] = {'success': True, 'content_length': len(markdown_content)}

        # Step 2: Extract topics
        logger.info("\n📍 Step 2: Extracting topics...")
        topics = await self.extract_topics(markdown_content, url)

        if not topics:
            logger.error("❌ Pipeline failed: No topics extracted")
            result['error'] = 'No topics extracted'
            return result

        result['steps']['extraction'] = {'success': True, 'topics_count': len(topics)}

        # Step 3: Merge and format (dual-mode)
        logger.info("\n📍 Step 3: Merging and formatting (dual-mode)...")
        documents = self.merge_and_format_dual_mode(topics)

        if not documents:
            logger.error("❌ Pipeline failed: Merge error")
            result['error'] = 'Merge failed'
            return result

        result['steps']['merge'] = {
            'success': True,
            'documents_count': len(documents),
            'full_doc_count': sum(1 for d in documents if d['mode'] == 'full_doc'),
            'paragraph_count': sum(1 for d in documents if d['mode'] == 'paragraph')
        }

        # Step 4: Save to PostgreSQL
        logger.info("\n📍 Step 4: Saving to PostgreSQL...")
        save_result = await self.save_to_postgresql(documents, url)

        if not save_result.get('success', False):
            logger.error("❌ Pipeline failed: Save error")
            result['error'] = save_result.get('error', 'Save failed')
            return result

        result['steps']['postgresql'] = save_result

        # Step 5 (Optional): Save to Dify
        if self.save_to_dify:
            logger.info("\n📍 Step 5: Saving to Dify (placeholder)...")
            await self.save_to_dify_placeholder(topics, url)
            result['steps']['dify'] = {'placeholder': True}

        # Success!
        result['success'] = True

        logger.info("\n" + "=" * 80)
        logger.info("✅ PIPELINE COMPLETE")
        logger.info("=" * 80)
        logger.info(f"📊 Summary:")
        logger.info(f"  • Topics extracted: {len(topics)}")
        logger.info(f"  • Documents created: {len(documents)}")
        logger.info(f"  • Full-doc: {result['steps']['merge']['full_doc_count']}")
        logger.info(f"  • Paragraph: {result['steps']['merge']['paragraph_count']}")
        logger.info(f"  • Saved to PostgreSQL: ✅")
        if self.save_to_dify:
            logger.info(f"  • Saved to Dify: ⏸️  (placeholder)")

        return result

    async def process_urls_batch(self, urls: List[str]) -> List[Dict]:
        """
        Process multiple URLs in sequence.

        Args:
            urls: List of URLs to process

        Returns:
            List of result dictionaries
        """
        logger.info("=" * 80)
        logger.info(f"🚀 BATCH PROCESSING: {len(urls)} URLs")
        logger.info("=" * 80)

        results = []

        for i, url in enumerate(urls, 1):
            logger.info(f"\n[{i}/{len(urls)}] Processing: {url}")
            result = await self.process_url(url)
            results.append(result)

            # Brief pause between URLs
            if i < len(urls):
                await asyncio.sleep(2)

        # Summary
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful

        logger.info("\n" + "=" * 80)
        logger.info("📊 BATCH SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total URLs: {len(urls)}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")

        return results


async def main():
    """Example usage of unified pipeline."""
    load_dotenv()

    # Database configuration
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'crawl4ai'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres'),
        'port': int(os.getenv('DB_PORT', 5432))
    }

    # Initialize pipeline
    pipeline = UnifiedPipeline(
        db_config=db_config,
        gemini_api_key=os.getenv('GEMINI_API_KEY'),
        save_to_dify=False  # Set to True later when ready
    )

    # Example: Process single URL
    result = await pipeline.process_url('https://docs.eosnetwork.com/docs/latest/quick-start/')

    # Save result to file
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    result_file = output_dir / f"pipeline_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2)

    logger.info(f"\n💾 Result saved to: {result_file}")

    # Example: Process multiple URLs
    # urls = [
    #     'https://docs.eosnetwork.com/docs/latest/quick-start/',
    #     'https://docs.eosnetwork.com/docs/latest/getting-started/',
    # ]
    # results = await pipeline.process_urls_batch(urls)


if __name__ == "__main__":
    asyncio.run(main())
