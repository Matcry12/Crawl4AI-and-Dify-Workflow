import asyncio
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from datetime import datetime
async def main():
    # Configure browser and crawler settings (using defaults here)
    browser_config = BrowserConfig()
    run_config = CrawlerRunConfig()
    
    # Initialize the crawler
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Set the URL you want to crawl
        url = "https://docs.eosnetwork.com/docs/latest/core-concepts/blockchain-basics/decentralization"
        # Run the crawler
        result = await crawler.arun(url=url, config=run_config)
        
        # Display results
        print(f"Crawl successful: {result.success}")
        print(f"Status code: {result.status_code}")
        # Save the result to a file in the output directory
        # Create the output directory if it doesn't exist
        import os
        os.makedirs("output", exist_ok=True)
        
        # Save the result to a file in the output directory
        with open("output/crawl_result.md", "w") as f:
            f.write(result.markdown)
        
        # Uncomment these to see other available data
        print("\n--- Raw HTML ---\n")
        print(result.html) # First 500 chars
        
        # print("\n--- Cleaned HTML ---\n")
        # print(result.cleaned_html[:500] + "...") # First 500 chars

if __name__ == "__main__":
    asyncio.run(main()) 