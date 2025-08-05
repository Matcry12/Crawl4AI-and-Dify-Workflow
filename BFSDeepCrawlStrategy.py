import asyncio
import os
from typing import List
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, LLMConfig, CacheMode
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.extraction_strategy import LLMExtractionStrategy

class PageMetadata(BaseModel):
    title: str
    author: str = None
    date: str = None
    topics: List[str] = []


async def main():
    # Configure a 2-level deep crawl
    
    api_key = os.getenv('OPENROUTER_API_KEY')

    llm_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="openrouter/deepseek/deepseek-r1:free", 
            api_token=api_key
        ),
        schema=PageMetadata,
        extraction_type="schema",
        instruction=(
            "Extract the title, author (if available), publication date (if available), "
            "and up to 5 main topics or keywords from the page."
        ),
        chunk_token_threshold=1000,
        overlap_rate=0.0,
        apply_chunking=True,
        input_format="markdown",  # or "html", "fit_markdown"
        extra_args={"temperature": 0.0, "max_tokens": 5000}
    )

    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=0, 
            include_external=False
        ),
        extraction_strategy=llm_strategy,
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True
    )

    run_config = CrawlerRunConfig(
        extraction_strategy=llm_strategy,
        cache_mode=CacheMode.BYPASS
    )

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun("https://docs.eosnetwork.com/docs/latest/quick-start/introduction", config=run_config)

        print(f"Crawled {len(results)} pages in total")

        print(results.markdown)

        if hasattr(llm_strategy, 'show_usage'):
            llm_strategy.show_usage()

        #for result in results:
            #print(result.markdown)

if __name__ == "__main__":
    asyncio.run(main())
