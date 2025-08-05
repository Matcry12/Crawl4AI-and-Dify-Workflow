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

async def push_to_dify(result_data, url, index):
    """Push comprehensive result to Dify.ai knowledge base."""
    # Push ONLY the description content - no title, name, or URL
    # Description already contains proper \n\n separators for Dify chunking
    markdown_content = result_data.get('description', '')
    
    payload = {
        "name": f"{result_data.get('title', 'Document')}_{index}",
        "text": markdown_content,
        "indexing_technique": "high_quality",
        "process_rule": {
            "mode": "automatic"
        }
    }

    try:
        response = requests.post(DIFY_API_URL, json=payload, headers=HEADERS)
        response.raise_for_status()
        print(f"✅ Successfully pushed document to Dify.ai")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to push document: {e}")
        return None
    
async def main():
    """
    Optimized crawler that extracts ONE comprehensive entry per webpage.
    """
    # Get API key from environment
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Warning: No GEMINI_API_KEY provided. Set GEMINI_API_KEY environment variable")
    
    # Configure browser settings
    browser_config = BrowserConfig(
        headless=True,
        verbose=False
    )
    
    # Load optimized instruction
    try:
        with open("prompts/extraction_prompt_optimized.txt", "r") as f:
            instruction = f.read()
    except FileNotFoundError:
        instruction = """Extract ONE comprehensive summary from the ENTIRE page content.
Put ALL information into the description field with sections separated by \\n\\n for optimal chunking:
overview, core facts, people/dates/events, keywords/categories, statistics, context/background, significance.
Total 300-800 words. Output only ONE JSON object."""
    
    url = "https://eosnetwork.com/"
    
    # Configure LLM extraction strategy - NO CHUNKING
    llm_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="gemini/gemini-2.5-flash-lite", 
            api_token=api_key
        ),
        schema=ResultSchema.model_json_schema(),
        extraction_type="schema",
        instruction=instruction,
        chunk_token_threshold=1000000,  # Extremely high to prevent chunking
        overlap_rate=0.0,
        apply_chunking=False,  # Explicitly disable chunking
        input_format="markdown",
        extra_args={
            "temperature": 0.0,
            "max_tokens": 3000  # Increased to accommodate comprehensive descriptions
        }
    )
    
    # Configure crawler with BFS deep crawl
    run_config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=1,
            include_external=False,
            max_pages=10
        ),
        extraction_strategy=llm_strategy,
        cache_mode=CacheMode.BYPASS,
        stream=True
    )
        
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    # Initialize and run crawler
    async with AsyncWebCrawler(config=browser_config) as crawler:
        print(f"Starting optimized crawl from: {url}")
        print("Configuration: ONE comprehensive entry per page")
        print("-" * 80)
        
        result_stream = await crawler.arun(url=url, config=run_config)
        
        crawled_count = 0
        extracted_files = []
        push_results = []
        
        try:
            async for page_result in result_stream:
                crawled_count += 1
                print(f"\n[Page {crawled_count}] {page_result.url}")
                print(f"  Status: {'✓' if page_result.success else '✗'}")
                
                if not page_result.success:
                    print(f"  Error: {page_result.error_message}")
                    continue
                
                if page_result.extracted_content:
                    try:
                        # Parse extracted data
                        if isinstance(page_result.extracted_content, str):
                            extracted_data = json.loads(page_result.extracted_content)
                        else:
                            extracted_data = page_result.extracted_content
                        
                        # Ensure single entry
                        if isinstance(extracted_data, list):
                            if len(extracted_data) > 1:
                                print(f"  Warning: Multiple entries found ({len(extracted_data)}), using first one")
                            extracted_data = extracted_data[0] if extracted_data else {}
                        
                        # Validate data
                        if not extracted_data or not extracted_data.get('description'):
                            print("  ⏭️  Skipping - no valid content extracted")
                            continue
                        
                        # Create safe filename
                        url_filename = page_result.url.replace("https://", "").replace("http://", "")
                        url_filename = url_filename.replace("/", "_").replace("?", "_").replace(":", "_")
                        if len(url_filename) > 100:
                            url_filename = url_filename[:100]
                        
                        # Save JSON
                        json_file = Path(output_dir) / f"{url_filename}.json"
                        with open(json_file, "w", encoding="utf-8") as f:
                            json.dump(extracted_data, f, indent=2, ensure_ascii=False)
                        
                        extracted_files.append(str(json_file))
                        print(f"  Saved: {json_file}")
                        
                        # Display summary
                        print(f"  Title: {extracted_data.get('title', 'N/A')}")
                        desc = extracted_data.get('description', '')
                        desc_length = len(desc)
                        chunk_count = desc.count('\n\n') + 1
                        print(f"  Description: {desc_length} characters in {chunk_count} chunks")
                        desc_preview = desc.replace('\n\n', ' | ')[:200] + "..."
                        print(f"  Preview: {desc_preview}")
                        
                        # Push to Dify
                        push_response = await push_to_dify(extracted_data, page_result.url, crawled_count)
                        
                        push_results.append({
                            'url': page_result.url,
                            'title': extracted_data.get('title', 'Untitled'),
                            'success': push_response is not None,
                            'response': push_response
                        })
                        
                    except Exception as e:
                        print(f"  Error processing content: {e}")
                else:
                    print("  No content extracted")
                    
        except Exception as e:
            print(f"\nError during crawling: {e}")
        
        # Final summary
        print("\n" + "=" * 80)
        print("CRAWL SUMMARY")
        print("=" * 80)
        print(f"Total pages crawled: {crawled_count}")
        print(f"Total comprehensive entries extracted: {len(extracted_files)}")
        print(f"Average entry per page: 1.0 (optimized)")
        
        if push_results:
            successful = sum(1 for p in push_results if p['success'])
            print(f"\nDify Push Results: {successful}/{len(push_results)} successful")
        
        # Show token usage
        if hasattr(llm_strategy, 'show_usage'):
            print("\nToken Usage (Optimized):")
            llm_strategy.show_usage()

if __name__ == "__main__":
    load_dotenv(override=True)
    asyncio.run(main())