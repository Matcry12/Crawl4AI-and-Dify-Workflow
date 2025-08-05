import asyncio
import os
import logging
import aiohttp
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from pydantic import BaseModel
from typing import List

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the schema for LLM extraction
class PageMetadata(BaseModel):
    title: str
    author: str = None
    date: str = None
    topics: List[str] = []

async def push_to_dify(session, metadata, markdown, url, api_url, api_key):
    """Push markdown content to Dify's knowledge base asynchronously."""
    name = metadata.title if metadata.title else url.split('/')[-1] or "Untitled"
    payload = {
        "name": name,
        "text": markdown,
        "indexing_technique": "high_quality",
        "process_rule": {"mode": "automatic"}
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    try:
        async with session.post(api_url, json=payload, headers=headers) as response:
            if response.status == 200:
                logger.info(f"[✓] Data pushed successfully for {url}")
            else:
                logger.warning(f"[!] Failed to push data for {url}: {response.status}")
                logger.warning(f" → Response: {await response.text()}")
    except aiohttp.ClientError as e:
        logger.error(f"[!] Exception during API push for {url}: {e}")

async def main():
    # Load configuration from environment variables
    api_base_url = os.getenv("DIFY_API_BASE_URL", "https://api.dify.ai")
    dataset_id = os.getenv("DIFY_DATASET_ID")
    api_key = os.getenv("DIFY_API_KEY")
    openrouter_api = os.getenv("OPENROUTER_API_KEY")
    if not dataset_id or not api_key:
        raise ValueError("DIFY_DATASET_ID and DIFY_API_KEY must be set in environment variables.")

    api_url = f"{api_base_url}/v1/datasets/{dataset_id}/document/create_by_text"

    # Configure LLM for metadata extraction
    llm_config = LLMConfig(provider="openrouter/deepseek/deepseek-r1:free", api_token=openrouter_api)
    strategy = LLMExtractionStrategy(
        schema=PageMetadata,
        instruction=(
            "Extract the title, author (if available), publication date (if available), "
            "and up to 5 main topics or keywords from the page."
        ),
        llm_config=llm_config,
        extract_type="pydantic",
    )

    # Configure crawler
    run_config = CrawlerRunConfig(
        crawl_strategy="bfs",
        max_pages=50,  # Increased from 10 for broader coverage
        extraction_strategy=strategy,
        word_count_threshold=1000,
        cache_mode="ENABLED",
        excluded_tags=["nav", "footer"]
    )

    async with AsyncWebCrawler() as crawler, aiohttp.ClientSession() as session:
        results = await crawler.crawl(url="https://example.com", config=run_config)

        for i, result in enumerate(results, 1):
            logger.info(f"[{i}/{len(results)}] Processing {result.url}")
            try:
                metadata = result.extracted_content
                markdown = result.markdown
                if markdown.strip():
                    await push_to_dify(session, metadata, markdown, result.url, api_url, api_key)
                else:
                    logger.warning(f"No markdown content for {result.url}, skipping...")
            except Exception as e:
                logger.error(f"[!] Failed to process {result.url}: {e}")

if __name__ == "__main__":
    asyncio.run(main())