#!/usr/bin/env python3
"""
Example of running the intelligent crawl workflow.
This script demonstrates how to use the CrawlWorkflow class.
"""

import asyncio
import os
from dotenv import load_dotenv
from crawl_workflow import CrawlWorkflow

async def main():
    # Load environment variables
    load_dotenv(override=True)
    
    # Initialize workflow with your API keys
    workflow = CrawlWorkflow(
        dify_base_url="http://localhost:8088",
        dify_api_key="dataset-VoYPMEaQ8L1udk2F6oek99XK",  # Replace with your actual Dify API key
        gemini_api_key=os.getenv('GEMINI_API_KEY')
    )
    
    # Example 1: Crawl a documentation site
    print("Example 1: Crawling documentation site...")
    await workflow.crawl_and_process(
        url="https://eosnetwork.com/",
        max_pages=5,
        max_depth=1
    )
    
    # Example 2: Crawl a different type of site (uncomment to use)
    # print("\nExample 2: Crawling news/blog site...")
    # await workflow.crawl_and_process(
    #     url="https://blog.example.com/",
    #     max_pages=3,
    #     max_depth=0
    # )

if __name__ == "__main__":
    print("🚀 Starting Intelligent Crawl Workflow Example")
    print("=" * 60)
    asyncio.run(main())