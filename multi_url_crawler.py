import asyncio
import os
import json
from pathlib import Path
from typing import List
from models.schemas import ResultSchema
from crawl4ai import (
    AsyncWebCrawler, 
    CrawlerRunConfig, 
    CacheMode, 
    BrowserConfig, 
    SemaphoreDispatcher, 
    RateLimiter
)

async def read_urls_from_json(file_path: str) -> List[str]:
    """Read URLs from a JSON file containing a list of ResultSchema objects."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")
    
    with open(path, 'r') as f:
        data = json.load(f)
    
    # Extract URLs from the JSON data
    urls = []
    for item in data:
        # Create a ResultSchema from each item to validate the structure
        workflow = ResultSchema(**item)
        urls.append(workflow.url)
    
    return urls

async def crawl_urls(
    urls: List[str], 
    semaphore_count: int = 5,
    check_robots_txt: bool = True,
    cache_mode: CacheMode = CacheMode.ENABLED,
    output_dir: str = None
):
    """Crawl multiple URLs with semaphore-based concurrency and robots.txt respect."""
    browser_config = BrowserConfig(
        headless=True, 
        verbose=False
    )
    
    run_config = CrawlerRunConfig(
        cache_mode=cache_mode,
        check_robots_txt=check_robots_txt,  # Respect robots.txt
        stream=False  # Disable streaming results to fix compatibility with SemaphoreDispatcher
    )

    # Configure dispatcher with semaphore and rate limiting
    dispatcher = SemaphoreDispatcher(
        semaphore_count=semaphore_count,  # Control concurrency
        rate_limiter=RateLimiter(
            base_delay=(1.0, 2.0),  # Random delay between 1 and 2 seconds
            max_delay=10.0  # Maximum delay after backoff
        )
    )

    # Setup output directory if provided
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)

    print(f"Starting crawl of {len(urls)} URLs with semaphore count: {semaphore_count}")
    print(f"Robots.txt checking: {'Enabled' if check_robots_txt else 'Disabled'}")
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        results = await crawler.arun_many(
            urls, 
            config=run_config,
            dispatcher=dispatcher
        )
        
        for result in results:
            if result.success:
                content_length = len(result.markdown.raw_markdown) if result.markdown else 0
                print(f"✅ {result.url} - {content_length} characters")
                
                # Save content to file if output directory is specified
                if output_dir:
                    url_filename = result.url.replace("://", "_").replace("/", "_").replace("?", "_")
                    if len(url_filename) > 100:
                        url_filename = url_filename[:100]  # Prevent extremely long filenames
                    
                    output_file = output_path / f"{url_filename}.md"
                    with open(output_file, "w", encoding="utf-8") as f:
                        f.write(result.markdown.raw_markdown if result.markdown else "")
                    print(f"   Saved to {output_file}")
            else:
                error_message = result.error_message or "Unknown error"
                if result.status_code == 403 and "robots.txt" in error_message:
                    print(f"🚫 {result.url} - Blocked by robots.txt")
                else:
                    print(f"❌ {result.url} - Error: {error_message}")
        
        return results

async def main():
    # Hardcoded configuration values
    urls_file = "output/https_bscscan.com_.json"
    semaphore_count = 5
    check_robots_txt = True
    cache_mode = CacheMode.ENABLED
    output_dir = "output"
    
    try:
        urls = await read_urls_from_json(urls_file)
        if not urls:
            print("No valid URLs found in the file.")
            return
        
        print(f"Found {len(urls)} URLs to crawl")
        
        await crawl_urls(
            urls=urls,
            semaphore_count=semaphore_count,
            check_robots_txt=check_robots_txt,
            cache_mode=cache_mode,
            output_dir=output_dir
        )
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 