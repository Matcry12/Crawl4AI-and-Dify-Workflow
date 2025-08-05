import asyncio
import requests
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy

# Dify.ai API configuration
DIFY_API_KEY = "dataset-VoYPMEaQ8L1udk2F6oek99XK"  # Replace with your Dify.ai API key
DIFY_API_URL = "http://localhost:8088/v1/datasets/7bf39c07-6d71-40cb-a036-43eb31696701/document/create_by_text"
HEADERS = {
    "Authorization": f"Bearer {DIFY_API_KEY}",
    "Content-Type": "application/json"
}

async def push_to_dify(markdown_content, url, index):
    """Push markdown content to Dify.ai knowledge base."""
    payload = {
        "name": f"Document_{index}_{url.split('/')[-1] or 'page'}",
        "text": markdown_content,
        "indexing_technique": "high_quality",
        "process_rule": {
            "mode": "automatic"
        }
    }

    try:
        response = requests.post(DIFY_API_URL, json=payload, headers=HEADERS)
        response.raise_for_status()
        print(f"✅ Successfully pushed document from {url} to Dify.ai")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to push document from {url}: {e}")
        return None

async def main():
    # Configure a 2-level deep crawl
    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=0,
            include_external=False
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        verbose=True
    )

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun("https://docs.eosnetwork.com/docs/latest/quick-start/introduction", config=config)

        print(f"Crawled {len(results)} pages in total")

        # Access individual results
        #for result in results[:3]:  # Show first 3 results+
        #    print(f"URL: {result.url}")
        #    print(f"Depth: {result.metadata.get('depth', 0)}")

        # Push each markdown result to Dify.ai
        for index, result in enumerate(results):
            if result.markdown:  # Ensure markdown content exists
                #await push_to_dify(result.markdown, result.url, index)
                print(result.markdown.references_markdown)
            else:
                print(f"No markdown content for {result.url}, skipping...")

if __name__ == "__main__":
    asyncio.run(main())