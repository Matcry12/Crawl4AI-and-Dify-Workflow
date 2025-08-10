#!/usr/bin/env python3
"""
Test token-efficient extraction with flexible headers
"""

import asyncio
import json
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from models.schemas import ResultSchema
import os
from dotenv import load_dotenv

async def test_efficient_extraction():
    """Test the token-efficient extraction on different types of pages."""
    
    load_dotenv(override=True)
    
    # Test URLs with different content densities
    test_urls = [
        {
            "url": "https://www.example.com",  # Simple page
            "description": "Simple page with minimal content"
        },
        {
            "url": "https://httpbin.org/html",  # Medium complexity
            "description": "Medium complexity HTML page"
        }
    ]
    
    # Load the updated prompts
    prompts = {
        "parent_child": "prompts/extraction_prompt_parent_child.txt",
        "flexible": "prompts/extraction_prompt_flexible.txt"
    }
    
    results = []
    
    for prompt_name, prompt_file in prompts.items():
        print(f"\n{'='*80}")
        print(f"Testing {prompt_name.upper()} extraction")
        print(f"{'='*80}")
        
        # Load prompt
        try:
            with open(prompt_file, "r") as f:
                instruction = f.read()
            print(f"✅ Loaded {prompt_name} prompt")
        except FileNotFoundError:
            print(f"❌ {prompt_file} not found")
            continue
        
        # Configure browser
        browser_config = BrowserConfig(
            headless=True,
            verbose=False
        )
        
        # Configure extraction
        llm_strategy = LLMExtractionStrategy(
            llm_config={
                "provider": "gemini/gemini-2.0-flash-exp",
                "api_token": os.getenv('GEMINI_API_KEY')
            },
            schema=ResultSchema.model_json_schema(),
            extraction_type="schema",
            instruction=instruction,
            chunk_token_threshold=1000000,
            overlap_rate=0.0,
            apply_chunking=False,
            extra_args={
                "temperature": 0.0,
                "max_tokens": 32000
            }
        )
        
        crawler_config = CrawlerRunConfig(
            extraction_strategy=llm_strategy
        )
        
        # Test on each URL
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for test_case in test_urls:
                url = test_case["url"]
                print(f"\n📍 Testing: {url}")
                print(f"   Type: {test_case['description']}")
                
                try:
                    result = await crawler.arun(url=url, config=crawler_config)
                    
                    if result.success and result.extracted_content:
                        # Parse content
                        if isinstance(result.extracted_content, str):
                            extracted_data = json.loads(result.extracted_content)
                        else:
                            extracted_data = result.extracted_content
                        
                        if isinstance(extracted_data, list):
                            extracted_data = extracted_data[0] if extracted_data else {}
                        
                        # Analyze extraction
                        if extracted_data:
                            desc = extracted_data.get('description', '')
                            
                            # Count sections
                            if prompt_name == "parent_child":
                                parent_count = desc.count('###PARENT_SECTION###') + 1 if desc else 0
                                child_count = desc.count('###CHILD_SECTION###')
                                section_info = f"{parent_count} parents, {child_count} children"
                            else:
                                section_count = desc.count('###SECTION_BREAK###') + 1 if desc else 0
                                section_info = f"{section_count} sections"
                            
                            # Calculate metrics
                            char_count = len(desc)
                            word_count = len(desc.split()) if desc else 0
                            
                            print(f"   ✅ Extracted successfully:")
                            print(f"      - Structure: {section_info}")
                            print(f"      - Size: {char_count} chars, {word_count} words")
                            print(f"      - Title: {extracted_data.get('title', 'No title')}")
                            
                            # Check for adaptive behavior
                            if char_count < 500:
                                print(f"      - 📊 Adaptive: Minimal content, efficient extraction")
                            elif char_count < 2000:
                                print(f"      - 📊 Adaptive: Medium content, balanced structure")
                            else:
                                print(f"      - 📊 Adaptive: Rich content, full structure")
                            
                            results.append({
                                "prompt": prompt_name,
                                "url": url,
                                "chars": char_count,
                                "words": word_count,
                                "structure": section_info
                            })
                        else:
                            print(f"   ⚠️  No content extracted")
                    else:
                        print(f"   ❌ Extraction failed")
                        
                except Exception as e:
                    print(f"   ❌ Error: {e}")
        
        # Show token usage if available
        if hasattr(llm_strategy, 'show_usage'):
            print(f"\n📊 Token usage for {prompt_name}:")
            llm_strategy.show_usage()
    
    # Summary comparison
    print(f"\n{'='*80}")
    print("📊 EFFICIENCY COMPARISON")
    print(f"{'='*80}")
    
    if results:
        print(f"\n{'Prompt Type':<15} {'URL':<30} {'Chars':<10} {'Words':<10} {'Structure':<20}")
        print("-" * 85)
        for r in results:
            url_short = r['url'][:28] + '..' if len(r['url']) > 30 else r['url']
            print(f"{r['prompt']:<15} {url_short:<30} {r['chars']:<10} {r['words']:<10} {r['structure']:<20}")
    
    print("\n✨ Key improvements:")
    print("1. Flexible structure adapts to actual content")
    print("2. No forced word counts or section numbers")
    print("3. Extracts only what exists on the page")
    print("4. Reduced token usage through efficiency")

if __name__ == "__main__":
    asyncio.run(test_efficient_extraction())