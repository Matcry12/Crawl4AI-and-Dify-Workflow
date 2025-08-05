import asyncio
import json
import os
from pathlib import Path
import requests

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from dotenv import load_dotenv
from models.schemas import ResultSchema


# Dify.ai API configuration
DIFY_API_KEY = "dataset-VoYPMEaQ8L1udk2F6oek99XK"  # Replace with your Dify.ai API key
DIFY_API_URL = "http://localhost:8088/v1/datasets/3fc5190f-4164-4847-b331-10528c1e60b9/document/create_by_text"
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
    """
    Crawl a URL and extract structured JSON data using LLM with BFS deep crawling.
    """
    # Get API key from args or environment
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Warning: No GEMINI_API_KEY provided. Set GEMINI_API_KEY environment variable")
    
    # Configure browser settings
    browser_config = BrowserConfig(
        headless=True,
        verbose=False
    )
    
    # Load instruction from file
    try:
        with open("prompts/extraction_prompt.txt", "r") as f:
            instruction = f.read()
    except FileNotFoundError:
        print("Warning: extraction_prompt.txt not found. Using default instruction.")
        instruction = "Extract structured data in the Results according to the schema."
    
    url = "https://beebom.com/grow-a-garden-cooking-recipe-list/"
    
    # 1. Define the LLM extraction strategy
    llm_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="gemini/gemini-2.5-flash-lite", 
            api_token=api_key
        ),
        schema=ResultSchema.model_json_schema(),
        extraction_type="schema",
        instruction=instruction,
        chunk_token_threshold=1000,
        overlap_rate=0.0,
        apply_chunking=True,
        input_format="markdown",
        extra_args={"temperature": 0.0, "max_tokens": 5000}
    )
    
    # 2. Configure the crawler run with BFS deep crawl strategy
    run_config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=0,  # Crawl 1 level deep
            include_external=False,
            max_pages=10  # Limit to 10 pages
        ),
        extraction_strategy=llm_strategy,
        cache_mode=CacheMode.BYPASS,
        stream=True  # MUST be True for deep crawl to return multiple results
    )
        
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    # Initialize the crawler
    async with AsyncWebCrawler(config=browser_config) as crawler:
        print(f"Starting BFS deep crawl from: {url}")
        print(f"Max depth: {run_config.deep_crawl_strategy.max_depth}")
        print(f"Max pages: {run_config.deep_crawl_strategy.max_pages}")
        print("-" * 80)
        
        # Run the crawler with LLM extraction
        result_stream = await crawler.arun(url=url, config=run_config)
        
        # Process all crawled pages
        crawled_count = 0
        extracted_files = []
        push_results = []  # Track push status
        
        # With stream=True and deep_crawl_strategy, arun returns an async generator
        try:
            async for page_result in result_stream:
                crawled_count += 1
                print(f"\n[Page {crawled_count}] {page_result.url}")
                print(f"  Status: {'✓' if page_result.success else '✗'}")
                
                if not page_result.success:
                    print(f"  Error: {page_result.error_message}")
                    continue
                
                # Process extracted content
                if page_result.extracted_content:
                    try:
                        # Parse the extracted data
                        if isinstance(page_result.extracted_content, str):
                            extracted_data = json.loads(page_result.extracted_content)
                        else:
                            extracted_data = page_result.extracted_content
                        
                        # Create safe filename from URL
                        url_filename = page_result.url.replace("https://", "").replace("http://", "")
                        url_filename = url_filename.replace("/", "").replace("?", "").replace(":", "_")
                        if len(url_filename) > 100:
                            url_filename = url_filename[:100]
                        
                        # Save JSON file
                        json_file = Path(output_dir) / f"{url_filename}.json"
                        with open(json_file, "w", encoding="utf-8") as f:
                            json.dump(extracted_data, f, indent=2, ensure_ascii=False)
                        
                        # Save markdown file if available
                        if hasattr(page_result, 'markdown') and page_result.markdown:
                            markdown_file = Path(output_dir) / f"{url_filename}.md"
                            with open(markdown_file, "w", encoding="utf-8") as f:
                                f.write(page_result.markdown.raw_markdown)
                        
                        extracted_files.append(str(json_file))
                        print(f"  Extracted: {json_file}")
                        
                        # Show a preview of extracted data and push to Dify immediately
                        # Handle both data structures: list directly or dict with 'results' key
                        results_to_process = []
                        
                        if isinstance(extracted_data, list):
                            # Data is directly a list of results
                            results_to_process = extracted_data
                        elif isinstance(extracted_data, dict) and 'results' in extracted_data:
                            # Data is a dict with 'results' key
                            results_to_process = extracted_data['results']
                        elif isinstance(extracted_data, dict):
                            # Data is a single dict result, wrap it in a list
                            results_to_process = [extracted_data]
                        
                        if results_to_process:
                            print(f"  Found {len(results_to_process)} items")
                            
                            # Push each result to Dify immediately after extraction
                            for idx, result in enumerate(results_to_process, 1):
                                # Check if description is null or too short
                                description = result.get('description', '')
                                if not description or len(description.strip()) < 10:
                                    print(f"    ⏭️  Skipping item {idx} - description is null or too short")
                                    continue
                                
                                # Create clear markdown content from title and description
                                markdown_content = f"""# {result.get('title', 'Untitled')}

{description}

---
Source: {page_result.url}
"""
                                # Push to Dify immediately
                                push_response = await push_to_dify(markdown_content, page_result.url, crawled_count * 100 + idx)
                                
                                # Track push status
                                push_status = {
                                    'url': page_result.url,
                                    'title': result.get('title', 'Untitled'),
                                    'success': push_response is not None,
                                    'response': push_response
                                }
                                push_results.append(push_status)
                                
                                if push_response:
                                    print(f"    ✅ Pushed item {idx}/{len(results_to_process)} to Dify")
                                else:
                                    print(f"    ❌ Failed to push item {idx}/{len(results_to_process)} to Dify")
                        else:
                            print("  No valid results found to push to Dify")
                        
                    except Exception as e:
                        print(f"  Error processing extracted content: {e}")
                else:
                    print("  No content extracted")
                    
        except Exception as e:
            print(f"\nError during crawling: {e}")
        
        # Print final summary
        print("\n" + "=" * 80)
        print("CRAWL SUMMARY")
        print("=" * 80)
        print(f"Total pages crawled: {crawled_count}")
        print(f"Total files extracted: {len(extracted_files)}")
        
        if extracted_files:
            print("\nExtracted files:")
            for i, file_path in enumerate(extracted_files, 1):
                print(f"  {i}. {file_path}")
        else:
            print("\nNo files were extracted.")
        
        # Push status summary
        print("\n" + "-" * 80)
        print("DIFY PUSH STATUS")
        print("-" * 80)
        
        if push_results:
            successful_pushes = [p for p in push_results if p['success']]
            failed_pushes = [p for p in push_results if not p['success']]
            
            print(f"Total items pushed: {len(push_results)}")
            print(f"✅ Successful: {len(successful_pushes)}")
            print(f"❌ Failed: {len(failed_pushes)}")
            
            if successful_pushes:
                print("\nSuccessfully pushed items:")
                for i, push in enumerate(successful_pushes, 1):
                    print(f"  {i}. {push['title']} (from {push['url']})")
            
            if failed_pushes:
                print("\nFailed to push items:")
                for i, push in enumerate(failed_pushes, 1):
                    print(f"  {i}. {push['title']} (from {push['url']})")
        else:
            print("No items were pushed to Dify.")
        
        # Show usage statistics if available
        if hasattr(llm_strategy, 'show_usage'):
            print("\nLLM Usage Statistics:")
            llm_strategy.show_usage()

if __name__ == "__main__":
    load_dotenv(override=True)
    asyncio.run(main())